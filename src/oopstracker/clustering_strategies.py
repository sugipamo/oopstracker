"""
Clustering strategies for function grouping.
Implements Strategy pattern to separate different clustering approaches.
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set
from collections import defaultdict

from .clustering_models import FunctionGroup, ClusteringStrategy

logger = logging.getLogger(__name__)


class ClusteringStrategyBase(ABC):
    """Base class for clustering strategies."""
    
    def __init__(self, min_cluster_size: int = 3):
        self.min_cluster_size = min_cluster_size
        self.logger = logger
    
    @abstractmethod
    async def cluster(self, functions: List[Dict[str, Any]], **kwargs) -> List[FunctionGroup]:
        """Perform clustering on the given functions."""
        pass
    
    def _create_function_group(
        self, 
        group_id: str, 
        functions: List[Dict[str, Any]], 
        label: str,
        confidence: float,
        metadata: Dict[str, Any]
    ) -> FunctionGroup:
        """Helper method to create FunctionGroup with consistent structure."""
        return FunctionGroup(
            group_id=group_id,
            functions=functions,
            label=label,
            confidence=confidence,
            metadata=metadata
        )


class CategoryBasedClusteringStrategy(ClusteringStrategyBase):
    """Cluster functions by their classification categories."""
    
    def __init__(self, taxonomy_expert, min_cluster_size: int = 3):
        super().__init__(min_cluster_size)
        self.taxonomy_expert = taxonomy_expert
    
    async def cluster(self, functions: List[Dict[str, Any]], **kwargs) -> List[FunctionGroup]:
        """Cluster functions by category using taxonomy expert."""
        # Classify all functions
        function_data = [(func['code'], func['name']) for func in functions]
        classification_results = await self.taxonomy_expert.analyze_function_collection(function_data)
        
        # Group by category
        category_groups = defaultdict(list)
        for i, result in enumerate(classification_results):
            category = result.primary_category
            function_with_category = functions[i].copy()
            function_with_category['category'] = category
            function_with_category['confidence'] = result.confidence
            category_groups[category].append(function_with_category)
        
        # Create FunctionGroup objects
        clusters = []
        for category, group_functions in category_groups.items():
            if len(group_functions) >= self.min_cluster_size:
                cluster = self._create_function_group(
                    group_id=f"category_{category}_{len(clusters)}",
                    functions=group_functions,
                    label=f"{category.replace('_', ' ').title()} Functions",
                    confidence=sum(f['confidence'] for f in group_functions) / len(group_functions),
                    metadata={
                        'clustering_strategy': 'category_based',
                        'category': category,
                        'function_count': len(group_functions)
                    }
                )
                clusters.append(cluster)
        
        self.logger.info(f"Created {len(clusters)} category-based clusters")
        return clusters


class PatternBasedClusteringStrategy(ClusteringStrategyBase):
    """Cluster functions by naming patterns."""
    
    def __init__(self, min_cluster_size: int = 3):
        super().__init__(min_cluster_size)
        self.patterns = {
            'data_retrieval': ['get_', 'fetch_', 'load_', 'read_', 'retrieve_'],
            'data_modification': ['set_', 'update_', 'save_', 'write_', 'store_'],
            'validation': ['validate_', 'check_', 'verify_', 'is_', 'has_'],
            'construction': ['__init__', 'create_', 'build_', 'make_', 'new_'],
            'destruction': ['delete_', 'remove_', 'destroy_', 'cleanup_', 'clear_'],
            'transformation': ['convert_', 'transform_', 'parse_', 'format_'],
            'calculation': ['calculate_', 'compute_', 'count_', 'sum_', 'avg_'],
            'handler': ['handle_', 'on_', 'process_'],
            'test': ['test_', 'assert_', 'mock_'],
        }
    
    async def cluster(self, functions: List[Dict[str, Any]], **kwargs) -> List[FunctionGroup]:
        """Cluster functions by name patterns."""
        pattern_groups = defaultdict(list)
        
        for func in functions:
            name = func['name'].lower()
            matched = False
            
            # Check against defined patterns
            for pattern_type, prefixes in self.patterns.items():
                if any(name.startswith(prefix) for prefix in prefixes):
                    pattern_groups[pattern_type].append(func)
                    matched = True
                    break
            
            # If no pattern matched, try to extract pattern from common suffixes
            if not matched:
                if name.endswith(('_handler', '_processor', '_manager')):
                    pattern_groups['handler'].append(func)
                elif name.endswith(('_test', '_tests')):
                    pattern_groups['test'].append(func)
                else:
                    pattern_groups['general'].append(func)
        
        clusters = []
        for pattern, group_functions in pattern_groups.items():
            if len(group_functions) >= self.min_cluster_size:
                cluster = self._create_function_group(
                    group_id=f"pattern_{pattern}_{len(clusters)}",
                    functions=group_functions,
                    label=f"{pattern.replace('_', ' ').title()} Functions",
                    confidence=0.8,  # Pattern matching has good confidence
                    metadata={
                        'clustering_strategy': 'pattern_based',
                        'pattern': pattern,
                        'function_count': len(group_functions)
                    }
                )
                clusters.append(cluster)
        
        self.logger.info(f"Created {len(clusters)} pattern-based clusters")
        return clusters


class HybridClusteringStrategy(ClusteringStrategyBase):
    """Combine multiple clustering strategies."""
    
    def __init__(self, primary_strategy: ClusteringStrategyBase, 
                 secondary_strategy: ClusteringStrategyBase,
                 min_cluster_size: int = 3):
        super().__init__(min_cluster_size)
        self.primary_strategy = primary_strategy
        self.secondary_strategy = secondary_strategy
    
    async def cluster(self, functions: List[Dict[str, Any]], **kwargs) -> List[FunctionGroup]:
        """Apply hybrid clustering using primary and secondary strategies."""
        # Get clusters from both strategies
        primary_clusters = await self.primary_strategy.cluster(functions, **kwargs)
        secondary_clusters = await self.secondary_strategy.cluster(functions, **kwargs)
        
        # Track which functions are already clustered
        clustered_functions: Set[str] = set()
        for cluster in primary_clusters:
            for func in cluster.functions:
                clustered_functions.add(func['name'])
        
        # Add secondary clusters for unclustered functions
        final_clusters = list(primary_clusters)
        
        for sec_cluster in secondary_clusters:
            unclustered_functions = [
                f for f in sec_cluster.functions 
                if f['name'] not in clustered_functions
            ]
            
            if len(unclustered_functions) >= self.min_cluster_size:
                # Create new cluster with unclustered functions
                new_cluster = self._create_function_group(
                    group_id=f"hybrid_{sec_cluster.group_id}",
                    functions=unclustered_functions,
                    label=f"[Secondary] {sec_cluster.label}",
                    confidence=sec_cluster.confidence * 0.9,  # Slightly lower confidence
                    metadata={
                        **sec_cluster.metadata,
                        'clustering_strategy': 'hybrid',
                        'source': 'secondary'
                    }
                )
                final_clusters.append(new_cluster)
                
                # Update clustered set
                for func in unclustered_functions:
                    clustered_functions.add(func['name'])
        
        self.logger.info(f"Created {len(final_clusters)} hybrid clusters "
                        f"({len(primary_clusters)} primary, {len(final_clusters) - len(primary_clusters)} secondary)")
        return final_clusters


class ClusteringStrategyFactory:
    """Factory for creating clustering strategies."""
    
    @staticmethod
    def create_strategy(
        strategy_type: ClusteringStrategy,
        taxonomy_expert=None,
        min_cluster_size: int = 3
    ) -> ClusteringStrategyBase:
        """Create appropriate clustering strategy based on type."""
        if strategy_type == ClusteringStrategy.CATEGORY_BASED:
            if not taxonomy_expert:
                raise ValueError("Category-based strategy requires taxonomy_expert")
            return CategoryBasedClusteringStrategy(taxonomy_expert, min_cluster_size)
        
        elif strategy_type == ClusteringStrategy.SEMANTIC_SIMILARITY:
            # For now, use pattern-based as a proxy for semantic similarity
            return PatternBasedClusteringStrategy(min_cluster_size)
        
        elif strategy_type == ClusteringStrategy.HYBRID:
            if not taxonomy_expert:
                raise ValueError("Hybrid strategy requires taxonomy_expert")
            primary = CategoryBasedClusteringStrategy(taxonomy_expert, min_cluster_size)
            secondary = PatternBasedClusteringStrategy(min_cluster_size)
            return HybridClusteringStrategy(primary, secondary, min_cluster_size)
        
        else:
            raise ValueError(f"Unknown clustering strategy: {strategy_type}")