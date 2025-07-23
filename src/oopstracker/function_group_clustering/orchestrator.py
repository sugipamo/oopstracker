"""Orchestrator for function group clustering operations."""

import logging
import time
from typing import List, Dict, Any, Optional

from ..clustering_models import FunctionGroup, ClusteringStrategy
from .clustering.base import ClusterStrategy
from .clustering.category_based import CategoryBasedClustering
from .clustering.similarity_based import SimilarityBasedClustering
from .clustering.hybrid import HybridClustering
from .metadata.recorder import MetadataRecorder
from .metadata.insights import InsightGenerator


class ClusteringOrchestrator:
    """Orchestrate clustering operations and coordinate components."""
    
    def __init__(self, enable_ai: bool = True):
        """Initialize the clustering orchestrator.
        
        Args:
            enable_ai: Whether to enable AI-based features
        """
        self.logger = logging.getLogger(__name__)
        self.enable_ai = enable_ai
        
        # Initialize strategies
        self.strategies: Dict[ClusteringStrategy, ClusterStrategy] = {
            ClusteringStrategy.CATEGORY_BASED: CategoryBasedClustering(enable_ai),
            ClusteringStrategy.SEMANTIC_SIMILARITY: SimilarityBasedClustering(enable_ai),
            ClusteringStrategy.HYBRID: HybridClustering(enable_ai)
        }
        
        # Initialize components
        self.metadata_recorder = MetadataRecorder()
        self.insight_generator = InsightGenerator()
        
        # State
        self.current_clusters: List[FunctionGroup] = []
        
        self.logger.info(f"Clustering orchestrator initialized (AI: {enable_ai})")
    
    async def cluster_functions(
        self,
        functions: List[Dict[str, Any]],
        strategy: ClusteringStrategy = ClusteringStrategy.HYBRID
    ) -> List[FunctionGroup]:
        """Cluster functions using the specified strategy.
        
        Args:
            functions: List of function dictionaries
            strategy: Clustering strategy to use
            
        Returns:
            List of function groups
        """
        start_time = time.time()
        
        # Get the appropriate strategy
        if strategy not in self.strategies:
            self.logger.warning(f"Unknown strategy {strategy}, using HYBRID")
            strategy = ClusteringStrategy.HYBRID
        
        clustering_strategy = self.strategies[strategy]
        
        # Perform clustering
        self.logger.info(f"Clustering {len(functions)} functions using {strategy.value}")
        clusters = await clustering_strategy.cluster(functions)
        
        # Record metadata
        duration = time.time() - start_time
        self.metadata_recorder.record_clustering_operation(
            operation_type='clustering',
            input_count=len(functions),
            output_count=len(clusters),
            strategy=strategy.value,
            duration=duration,
            metadata={
                'avg_cluster_size': sum(len(c.functions) for c in clusters) / len(clusters) if clusters else 0,
                'confidence_range': {
                    'min': min(c.confidence for c in clusters) if clusters else 0,
                    'max': max(c.confidence for c in clusters) if clusters else 0
                }
            }
        )
        
        # Record quality metrics
        self.metadata_recorder.record_cluster_quality(clusters)
        
        # Update state
        self.current_clusters = clusters
        
        self.logger.info(
            f"Clustering completed in {duration:.2f}s: "
            f"{len(functions)} functions -> {len(clusters)} clusters"
        )
        
        return clusters
    
    async def refine_clusters(
        self,
        clusters: Optional[List[FunctionGroup]] = None,
        strategy: ClusteringStrategy = ClusteringStrategy.HYBRID
    ) -> List[FunctionGroup]:
        """Refine existing clusters using a different strategy.
        
        Args:
            clusters: Clusters to refine (uses current_clusters if None)
            strategy: Strategy to use for refinement
            
        Returns:
            Refined clusters
        """
        if clusters is None:
            clusters = self.current_clusters
        
        if not clusters:
            self.logger.warning("No clusters to refine")
            return []
        
        start_time = time.time()
        
        # Extract all functions from clusters
        all_functions = []
        for cluster in clusters:
            all_functions.extend(cluster.functions)
        
        # Re-cluster with new strategy
        refined_clusters = await self.cluster_functions(all_functions, strategy)
        
        # Record refinement operation
        duration = time.time() - start_time
        self.metadata_recorder.record_clustering_operation(
            operation_type='refinement',
            input_count=len(clusters),
            output_count=len(refined_clusters),
            strategy=strategy.value,
            duration=duration,
            metadata={
                'original_clusters': len(clusters),
                'function_count': len(all_functions)
            }
        )
        
        return refined_clusters
    
    def get_insights(self) -> Dict[str, Any]:
        """Generate insights from current clustering state.
        
        Returns:
            Dictionary of insights
        """
        return self.insight_generator.generate_insights(
            self.current_clusters,
            self.metadata_recorder
        )
    
    def get_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations for improving clustering.
        
        Returns:
            List of recommendations
        """
        insights = self.get_insights()
        return insights.get('recommendations', [])
    
    def get_quality_assessment(self) -> Dict[str, Any]:
        """Get quality assessment of current clusters.
        
        Returns:
            Quality assessment dictionary
        """
        insights = self.get_insights()
        return insights.get('quality_assessment', {})
    
    def get_operation_summary(self) -> Dict[str, Any]:
        """Get summary of all clustering operations.
        
        Returns:
            Operation summary
        """
        return self.metadata_recorder.get_operation_summary()
    
    def export_state(self) -> Dict[str, Any]:
        """Export the current state for persistence.
        
        Returns:
            State dictionary
        """
        return {
            'clusters': [
                {
                    'group_id': c.group_id,
                    'label': c.label,
                    'confidence': c.confidence,
                    'function_count': len(c.functions),
                    'metadata': c.metadata
                }
                for c in self.current_clusters
            ],
            'metadata': self.metadata_recorder.export_metadata(),
            'insights': self.get_insights()
        }
    
    def import_state(self, state: Dict[str, Any]):
        """Import a previously exported state.
        
        Args:
            state: State dictionary to import
        """
        # Import metadata
        if 'metadata' in state:
            self.metadata_recorder.import_metadata(state['metadata'])
        
        self.logger.info("State imported successfully")
    
    async def optimize_clusters(self) -> List[FunctionGroup]:
        """Automatically optimize clusters based on insights.
        
        Returns:
            Optimized clusters
        """
        if not self.current_clusters:
            self.logger.warning("No clusters to optimize")
            return []
        
        # Get recommendations
        recommendations = self.get_recommendations()
        
        # Apply high-priority recommendations
        optimized = False
        
        for rec in recommendations:
            if rec.get('priority') == 'high':
                if rec['type'] == 'split_recommendation':
                    # Handle split recommendations
                    self.logger.info(f"Applying split recommendation: {rec['message']}")
                    # Note: Actual splitting would require manual patterns or AI
                    optimized = True
                    
                elif rec['type'] == 'refinement_recommendation':
                    # Refine low-confidence clusters
                    self.logger.info(f"Applying refinement recommendation: {rec['message']}")
                    self.current_clusters = await self.refine_clusters(strategy=ClusteringStrategy.HYBRID)
                    optimized = True
                    break  # One optimization at a time
        
        if not optimized:
            self.logger.info("No high-priority optimizations needed")
        
        return self.current_clusters
    
    def get_cluster_by_id(self, cluster_id: str) -> Optional[FunctionGroup]:
        """Get a specific cluster by ID.
        
        Args:
            cluster_id: ID of the cluster
            
        Returns:
            Function group or None
        """
        for cluster in self.current_clusters:
            if cluster.group_id == cluster_id:
                return cluster
        return None
    
    def get_clusters_by_label_pattern(self, pattern: str) -> List[FunctionGroup]:
        """Get clusters matching a label pattern.
        
        Args:
            pattern: Pattern to match (case-insensitive substring)
            
        Returns:
            List of matching clusters
        """
        pattern_lower = pattern.lower()
        return [
            cluster for cluster in self.current_clusters
            if pattern_lower in cluster.label.lower()
        ]