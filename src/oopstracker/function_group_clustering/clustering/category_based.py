"""Category-based clustering strategy."""

import logging
from typing import List, Dict, Any
from collections import defaultdict

from .base import ClusterStrategy
from ...clustering_models import FunctionGroup
from ...function_taxonomy_expert import FunctionTaxonomyExpert


class CategoryBasedClustering(ClusterStrategy):
    """Cluster functions by their classification categories."""
    
    def __init__(self):
        """Initialize category-based clustering."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.taxonomy_expert = FunctionTaxonomyExpert()
        
    async def cluster(self, functions: List[Dict[str, Any]]) -> List[FunctionGroup]:
        """Cluster functions by their classification categories.
        
        Args:
            functions: List of function dictionaries
            
        Returns:
            List of function groups clustered by category
        """
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
        
        # Create function groups
        clusters = []
        for category, group_functions in category_groups.items():
            cluster = FunctionGroup(
                group_id=f"category_{category}",
                functions=group_functions,
                label=category,
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
    
    def get_strategy_name(self) -> str:
        """Get the name of the clustering strategy."""
        return "category_based"