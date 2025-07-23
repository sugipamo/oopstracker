"""
Clustering strategy implementations for function grouping.

This module contains the different clustering strategies extracted from
FunctionGroupClusteringSystem to promote separation of concerns.
"""

import logging
from typing import List, Dict, Any
from collections import defaultdict

from .clustering_models import FunctionGroup, ClusteringStrategy


class ClusteringStrategyManager:
    """Manages different clustering strategies for function grouping."""
    
    def __init__(self, taxonomy_expert, min_cluster_size: int = 3):
        self.logger = logging.getLogger(__name__)
        self.taxonomy_expert = taxonomy_expert
        self.min_cluster_size = min_cluster_size
    
    async def cluster_by_category(self, functions: List[Dict[str, Any]]) -> List[FunctionGroup]:
        """Group functions by their categorized intents."""
        categories = defaultdict(list)
        
        for func in functions:
            category = await self._get_function_category(func)
            categories[category].append(func)
        
        clusters = []
        for category, category_functions in categories.items():
            if len(category_functions) >= self.min_cluster_size:
                cluster = FunctionGroup(
                    group_id=f"category_{category.replace(' ', '_').lower()}",
                    functions=category_functions,
                    label=category,
                    confidence=0.8,
                    metadata={
                        'clustering_strategy': 'category',
                        'category': category,
                        'function_count': len(category_functions)
                    }
                )
                clusters.append(cluster)
        
        self.logger.info(f"Created {len(clusters)} category-based clusters")
        return clusters
    
    async def cluster_by_similarity(self, functions: List[Dict[str, Any]]) -> List[FunctionGroup]:
        """Group functions by semantic similarity patterns."""
        patterns = await self._extract_semantic_patterns(functions)
        pattern_groups = defaultdict(list)
        
        for func in functions:
            best_pattern = await self._find_best_pattern_match(func, patterns)
            if best_pattern:
                pattern_groups[best_pattern].append(func)
        
        clusters = []
        for pattern, group_functions in pattern_groups.items():
            if len(group_functions) >= self.min_cluster_size:
                cluster = FunctionGroup(
                    group_id=f"similarity_{hash(pattern) % 10000}",
                    functions=group_functions,
                    label=f"Pattern: {pattern[:50]}...",
                    confidence=0.7,
                    metadata={
                        'clustering_strategy': 'similarity',
                        'pattern': pattern,
                        'function_count': len(group_functions)
                    }
                )
                clusters.append(cluster)
        
        self.logger.info(f"Created {len(clusters)} similarity-based clusters")
        return clusters
    
    async def cluster_hybrid(self, functions: List[Dict[str, Any]]) -> List[FunctionGroup]:
        """Combine category and similarity-based clustering."""
        category_clusters = await self.cluster_by_category(functions)
        similarity_clusters = await self.cluster_by_similarity(functions)
        
        # Simple merge: prefer category-based, fall back to similarity
        final_clusters = category_clusters
        
        # Add similarity clusters for functions not in category clusters
        categorized_functions = set()
        for cluster in category_clusters:
            for func in cluster.functions:
                categorized_functions.add(func['name'])
        
        for sim_cluster in similarity_clusters:
            uncategorized_functions = [
                f for f in sim_cluster.functions 
                if f['name'] not in categorized_functions
            ]
            if len(uncategorized_functions) >= self.min_cluster_size:
                sim_cluster.functions = uncategorized_functions
                sim_cluster.group_id = f"hybrid_{sim_cluster.group_id}"
                final_clusters.append(sim_cluster)
        
        self.logger.info(f"Created {len(final_clusters)} hybrid clusters")
        return final_clusters
    
    async def _get_function_category(self, func: Dict[str, Any]) -> str:
        """Get the category for a function using taxonomy expert."""
        try:
            intent_info = await self.taxonomy_expert.analyze_function_intent(
                func.get('code', ''),
                func.get('name', '')
            )
            return intent_info.get('category', 'uncategorized')
        except Exception as e:
            self.logger.warning(f"Failed to categorize function {func.get('name')}: {e}")
            return 'uncategorized'
    
    async def _extract_semantic_patterns(self, functions: List[Dict[str, Any]]) -> List[str]:
        """Extract semantic patterns from function set."""
        # Simplified pattern extraction
        patterns = []
        
        # Extract common code patterns
        code_snippets = [func.get('code', '')[:100] for func in functions[:10]]
        for snippet in code_snippets:
            if len(snippet) > 20:
                patterns.append(snippet)
        
        return patterns
    
    async def _find_best_pattern_match(self, func: Dict[str, Any], patterns: List[str]) -> str:
        """Find the best matching pattern for a function."""
        func_code = func.get('code', '')
        
        # Simple substring matching (can be enhanced with more sophisticated matching)
        for pattern in patterns:
            if pattern in func_code:
                return pattern
        
        return None