"""Hybrid clustering strategy combining multiple approaches."""

import logging
from typing import List, Dict, Any, Set

from .base import ClusterStrategy
from .category_based import CategoryBasedClustering
from .similarity_based import SimilarityBasedClustering
from ...clustering_models import FunctionGroup


class HybridClustering(ClusterStrategy):
    """Combine category and similarity-based clustering approaches."""
    
    def __init__(self, enable_ai: bool = True):
        """Initialize hybrid clustering.
        
        Args:
            enable_ai: Whether to enable AI-based features
        """
        super().__init__(enable_ai)
        self.logger = logging.getLogger(__name__)
        self.category_strategy = CategoryBasedClustering(enable_ai)
        self.similarity_strategy = SimilarityBasedClustering(enable_ai)
        self.min_cluster_size = 3
        
    async def cluster(self, functions: List[Dict[str, Any]]) -> List[FunctionGroup]:
        """Cluster functions using a hybrid approach.
        
        This method combines category-based and similarity-based clustering
        to leverage the strengths of both approaches.
        
        Args:
            functions: List of function dictionaries
            
        Returns:
            List of function groups using hybrid clustering
        """
        # First, get category-based clusters
        category_clusters = await self.category_strategy.cluster(functions)
        
        # Then, get similarity-based clusters
        similarity_clusters = await self.similarity_strategy.cluster(functions)
        
        # Merge and refine clusters
        final_clusters = self._merge_clusters(category_clusters, similarity_clusters, functions)
        
        self.logger.info(f"Created {len(final_clusters)} hybrid clusters")
        return final_clusters
    
    def _merge_clusters(
        self, 
        category_clusters: List[FunctionGroup], 
        similarity_clusters: List[FunctionGroup],
        all_functions: List[Dict[str, Any]]
    ) -> List[FunctionGroup]:
        """Merge clusters from different strategies intelligently.
        
        Args:
            category_clusters: Clusters from category-based approach
            similarity_clusters: Clusters from similarity-based approach
            all_functions: All original functions
            
        Returns:
            Merged and refined clusters
        """
        # Track which functions have been assigned
        assigned_functions: Set[str] = set()
        final_clusters = []
        
        # First, use category clusters as the base
        for cat_cluster in category_clusters:
            # Find overlapping similarity clusters
            overlapping_sim_clusters = []
            cat_func_names = {f['name'] for f in cat_cluster.functions}
            
            for sim_cluster in similarity_clusters:
                sim_func_names = {f['name'] for f in sim_cluster.functions}
                overlap = len(cat_func_names & sim_func_names)
                
                if overlap > 0:
                    overlap_ratio = overlap / len(sim_func_names)
                    overlapping_sim_clusters.append((sim_cluster, overlap_ratio))
            
            # If there's significant overlap, refine the category cluster
            if overlapping_sim_clusters:
                refined_cluster = self._refine_cluster(cat_cluster, overlapping_sim_clusters)
                final_clusters.append(refined_cluster)
                assigned_functions.update(f['name'] for f in refined_cluster.functions)
            else:
                # Keep the category cluster as is
                final_clusters.append(cat_cluster)
                assigned_functions.update(f['name'] for f in cat_cluster.functions)
        
        # Add similarity clusters for unassigned functions
        for sim_cluster in similarity_clusters:
            unassigned_functions = [
                f for f in sim_cluster.functions 
                if f['name'] not in assigned_functions
            ]
            
            if len(unassigned_functions) >= self.min_cluster_size:
                new_cluster = FunctionGroup(
                    group_id=f"hybrid_{sim_cluster.group_id}",
                    functions=unassigned_functions,
                    label=sim_cluster.label,
                    confidence=sim_cluster.confidence * 0.9,  # Slightly lower confidence
                    metadata={
                        **sim_cluster.metadata,
                        'clustering_strategy': 'hybrid_similarity_only'
                    }
                )
                final_clusters.append(new_cluster)
                assigned_functions.update(f['name'] for f in unassigned_functions)
        
        # Handle any remaining unassigned functions
        unassigned = [
            f for f in all_functions 
            if f['name'] not in assigned_functions
        ]
        
        if len(unassigned) >= self.min_cluster_size:
            misc_cluster = FunctionGroup(
                group_id="hybrid_miscellaneous",
                functions=unassigned,
                label="Miscellaneous Functions",
                confidence=0.5,
                metadata={
                    'clustering_strategy': 'hybrid_unassigned',
                    'function_count': len(unassigned)
                }
            )
            final_clusters.append(misc_cluster)
        
        return final_clusters
    
    def _refine_cluster(
        self, 
        category_cluster: FunctionGroup,
        overlapping_sim_clusters: List[tuple]
    ) -> FunctionGroup:
        """Refine a category cluster based on similarity information.
        
        Args:
            category_cluster: The base category cluster
            overlapping_sim_clusters: List of (similarity_cluster, overlap_ratio) tuples
            
        Returns:
            Refined cluster
        """
        # Sort by overlap ratio
        overlapping_sim_clusters.sort(key=lambda x: x[1], reverse=True)
        
        # If there's a strong similarity pattern, use it to refine the label
        if overlapping_sim_clusters[0][1] > 0.7:
            sim_cluster = overlapping_sim_clusters[0][0]
            refined_label = f"{category_cluster.label} - {sim_cluster.label}"
            refined_confidence = (category_cluster.confidence + sim_cluster.confidence) / 2
        else:
            refined_label = category_cluster.label
            refined_confidence = category_cluster.confidence
        
        # Create refined cluster
        refined_cluster = FunctionGroup(
            group_id=f"hybrid_{category_cluster.group_id}",
            functions=category_cluster.functions,
            label=refined_label,
            confidence=refined_confidence,
            metadata={
                **category_cluster.metadata,
                'clustering_strategy': 'hybrid_refined',
                'base_strategy': 'category',
                'refinement_source': 'similarity',
                'overlap_ratios': [ratio for _, ratio in overlapping_sim_clusters[:3]]
            }
        )
        
        return refined_cluster
    
    def get_strategy_name(self) -> str:
        """Get the name of the clustering strategy."""
        return "hybrid"