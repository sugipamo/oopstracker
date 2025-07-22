"""
Category-based clustering strategy.
"""

import logging
from typing import List, Dict, Any
from collections import defaultdict

from .base import ClusteringStrategyBase
from ..clustering_models import FunctionGroup
from ..function_taxonomy_expert import FunctionTaxonomyExpert


class CategoryBasedStrategy(ClusteringStrategyBase):
    """Clusters functions based on their classification categories."""
    
    def __init__(self, taxonomy_expert: FunctionTaxonomyExpert, 
                 min_cluster_size: int = 3, max_cluster_size: int = 15):
        super().__init__(min_cluster_size, max_cluster_size)
        self.taxonomy_expert = taxonomy_expert
        self.logger = logging.getLogger(__name__)
    
    async def cluster(self, functions: List[Dict[str, Any]]) -> List[FunctionGroup]:
        """Cluster functions by their classification categories."""
        
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
                cluster = FunctionGroup(
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