"""
Function Group Clustering System for OOPStracker.
Groups related functions together for analysis and refactoring.
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from collections import defaultdict

from .function_categories import FunctionCategory


class ClusteringStrategy(Enum):
    """Clustering strategies for function grouping."""
    CATEGORY_BASED = "category_based"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    HYBRID = "hybrid"


@dataclass
class FunctionGroup:
    """Represents a group of related functions."""
    group_id: str
    functions: List[Dict[str, Any]]
    label: str
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.functions:
            self.functions = []
    
    @property
    def size(self) -> int:
        """Get the number of functions in this group."""
        return len(self.functions)
    
    def add_function(self, function: Dict[str, Any]):
        """Add a function to this group."""
        self.functions.append(function)
    
    def get_function_names(self) -> List[str]:
        """Get list of function names in this group."""
        return [func.get('name', 'unknown') for func in self.functions]


@dataclass
class ClusterSplitResult:
    """Result of splitting a cluster."""
    group_a: FunctionGroup
    group_b: FunctionGroup
    split_reason: str
    confidence: float = 0.8


class FunctionGroupClusteringSystem:
    """Main system for clustering functions into related groups."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._cached_clusters = {}
        
    async def load_all_functions_from_repository(self, code_units: List[Any]) -> List[Dict[str, Any]]:
        """Load all functions from code repository."""
        all_functions = []
        
        for unit in code_units:
            # CodeUnitオブジェクトから直接関数を取得
            if hasattr(unit, 'type') and unit.type == 'function':
                func_data = {
                    'name': unit.name,
                    'file': unit.file_path or 'unknown',
                    'signature': '',  # 署名は別途抽出が必要
                    'code': unit.source_code,
                    'category': FunctionCategory.UNKNOWN.value,
                    'line_number': unit.start_line,
                    'metadata': {
                        'hash': unit.hash,
                        'complexity': unit.complexity_score,
                        'dependencies': unit.dependencies
                    }
                }
                all_functions.append(func_data)
        
        self.logger.info(f"Loaded {len(all_functions)} functions from repository")
        return all_functions
    
    async def get_current_function_clusters(self, 
                                          functions: List[Dict[str, Any]], 
                                          strategy: ClusteringStrategy = ClusteringStrategy.CATEGORY_BASED) -> List[FunctionGroup]:
        """Get current function clusters using specified strategy."""
        
        if strategy == ClusteringStrategy.CATEGORY_BASED:
            return await self._cluster_by_category(functions)
        elif strategy == ClusteringStrategy.SEMANTIC_SIMILARITY:
            return await self._cluster_by_semantic_similarity(functions)
        elif strategy == ClusteringStrategy.HYBRID:
            return await self._cluster_hybrid(functions)
        else:
            return await self._cluster_by_category(functions)
    
    async def _cluster_by_category(self, functions: List[Dict[str, Any]]) -> List[FunctionGroup]:
        """Cluster functions by their categories."""
        category_groups = defaultdict(list)
        
        for func in functions:
            category = func.get('category', FunctionCategory.UNKNOWN.value)
            category_groups[category].append(func)
        
        clusters = []
        for category, func_list in category_groups.items():
            if func_list:  # Only create groups with functions
                group = FunctionGroup(
                    group_id=f"category_{category}",
                    functions=func_list,
                    label=f"{category.replace('_', ' ').title()} Functions",
                    confidence=0.9,
                    metadata={
                        'strategy': 'category_based',
                        'category': category
                    }
                )
                clusters.append(group)
        
        self.logger.info(f"Created {len(clusters)} category-based clusters")
        return clusters
    
    async def _cluster_by_semantic_similarity(self, functions: List[Dict[str, Any]]) -> List[FunctionGroup]:
        """Cluster functions by semantic similarity."""
        # Simple implementation - group by common prefixes in function names
        prefix_groups = defaultdict(list)
        
        for func in functions:
            name = func.get('name', '')
            # Extract common prefixes (first word before underscore)
            prefix = name.split('_')[0] if '_' in name else name[:3]
            prefix_groups[prefix].append(func)
        
        clusters = []
        for prefix, func_list in prefix_groups.items():
            if len(func_list) > 1:  # Only create groups with multiple functions
                group = FunctionGroup(
                    group_id=f"semantic_{prefix}",
                    functions=func_list,
                    label=f"Functions with '{prefix}' pattern",
                    confidence=0.7,
                    metadata={
                        'strategy': 'semantic_similarity',
                        'prefix': prefix
                    }
                )
                clusters.append(group)
        
        # Add remaining single functions to an "unclustered" group
        unclustered = []
        for prefix, func_list in prefix_groups.items():
            if len(func_list) == 1:
                unclustered.extend(func_list)
        
        if unclustered:
            group = FunctionGroup(
                group_id="semantic_unclustered",
                functions=unclustered,
                label="Unclustered Functions",
                confidence=0.5,
                metadata={'strategy': 'semantic_similarity'}
            )
            clusters.append(group)
        
        self.logger.info(f"Created {len(clusters)} semantic similarity clusters")
        return clusters
    
    async def _cluster_hybrid(self, functions: List[Dict[str, Any]]) -> List[FunctionGroup]:
        """Cluster functions using hybrid approach."""
        # Combine category and semantic clustering
        category_clusters = await self._cluster_by_category(functions)
        
        # Further split large category clusters by semantic similarity
        refined_clusters = []
        
        for cluster in category_clusters:
            if cluster.size > 5:  # Split large clusters
                sub_clusters = await self._cluster_by_semantic_similarity(cluster.functions)
                for sub_cluster in sub_clusters:
                    sub_cluster.group_id = f"{cluster.group_id}_{sub_cluster.group_id}"
                    sub_cluster.label = f"{cluster.label} - {sub_cluster.label}"
                    sub_cluster.metadata.update(cluster.metadata)
                    sub_cluster.metadata['parent_cluster'] = cluster.group_id
                refined_clusters.extend(sub_clusters)
            else:
                refined_clusters.append(cluster)
        
        self.logger.info(f"Created {len(refined_clusters)} hybrid clusters")
        return refined_clusters
    
    async def analyze_cluster_quality(self, clusters: List[FunctionGroup]) -> Dict[str, Any]:
        """Analyze the quality of clustering results."""
        total_functions = sum(cluster.size for cluster in clusters)
        
        # Calculate cluster statistics
        cluster_sizes = [cluster.size for cluster in clusters]
        avg_cluster_size = sum(cluster_sizes) / len(cluster_sizes) if cluster_sizes else 0
        
        # Find largest and smallest clusters
        largest_cluster = max(clusters, key=lambda c: c.size) if clusters else None
        smallest_cluster = min(clusters, key=lambda c: c.size) if clusters else None
        
        quality_metrics = {
            'total_clusters': len(clusters),
            'total_functions': total_functions,
            'average_cluster_size': round(avg_cluster_size, 2),
            'largest_cluster': {
                'id': largest_cluster.group_id,
                'size': largest_cluster.size,
                'label': largest_cluster.label
            } if largest_cluster else None,
            'smallest_cluster': {
                'id': smallest_cluster.group_id,
                'size': smallest_cluster.size,
                'label': smallest_cluster.label  
            } if smallest_cluster else None,
            'cluster_distribution': cluster_sizes
        }
        
        return quality_metrics
    
    async def suggest_cluster_splits(self, cluster: FunctionGroup) -> List[ClusterSplitResult]:
        """Suggest ways to split a large cluster."""
        if cluster.size < 4:
            return []  # Too small to split meaningfully
        
        suggestions = []
        
        # Split by file location
        file_groups = defaultdict(list)
        for func in cluster.functions:
            file_path = func.get('file', 'unknown')
            file_groups[file_path].append(func)
        
        if len(file_groups) > 1:
            # Create split based on most common files
            sorted_files = sorted(file_groups.items(), key=lambda x: len(x[1]), reverse=True)
            main_file_funcs = sorted_files[0][1]
            other_file_funcs = []
            for _, funcs in sorted_files[1:]:
                other_file_funcs.extend(funcs)
            
            if len(main_file_funcs) > 0 and len(other_file_funcs) > 0:
                group_a = FunctionGroup(
                    group_id=f"{cluster.group_id}_main_file",
                    functions=main_file_funcs,
                    label=f"{cluster.label} (Main File)",
                    confidence=0.8
                )
                
                group_b = FunctionGroup(
                    group_id=f"{cluster.group_id}_other_files",
                    functions=other_file_funcs,
                    label=f"{cluster.label} (Other Files)",
                    confidence=0.8
                )
                
                suggestions.append(ClusterSplitResult(
                    group_a=group_a,
                    group_b=group_b,
                    split_reason="Split by file location",
                    confidence=0.8
                ))
        
        return suggestions
    
    def export_clusters_to_dict(self, clusters: List[FunctionGroup]) -> Dict[str, Any]:
        """Export clusters to dictionary format."""
        return {
            'clusters': [
                {
                    'group_id': cluster.group_id,
                    'label': cluster.label,
                    'size': cluster.size,
                    'confidence': cluster.confidence,
                    'function_names': cluster.get_function_names(),
                    'metadata': cluster.metadata
                }
                for cluster in clusters
            ],
            'total_clusters': len(clusters),
            'total_functions': sum(cluster.size for cluster in clusters)
        }


async def demo_clustering_system():
    """Demo the clustering system."""
    system = FunctionGroupClusteringSystem()
    
    # Sample functions
    sample_functions = [
        {'name': 'get_user_name', 'category': 'getter', 'file': 'user.py'},
        {'name': 'set_user_name', 'category': 'setter', 'file': 'user.py'},
        {'name': 'get_user_email', 'category': 'getter', 'file': 'user.py'},  
        {'name': 'validate_email', 'category': 'validation', 'file': 'validators.py'},
        {'name': 'validate_password', 'category': 'validation', 'file': 'validators.py'},
        {'name': 'process_payment', 'category': 'business_logic', 'file': 'payments.py'},
        {'name': 'calculate_tax', 'category': 'business_logic', 'file': 'taxes.py'}
    ]
    
    print("🔍 Function Group Clustering Demo")
    print("=" * 40)
    
    for strategy in ClusteringStrategy:
        print(f"\n📊 Strategy: {strategy.value}")
        clusters = await system.get_current_function_clusters(sample_functions, strategy)
        
        for cluster in clusters:
            print(f"  📁 {cluster.label} ({cluster.size} functions)")
            for func_name in cluster.get_function_names():
                print(f"    - {func_name}")
    
    # Quality analysis
    quality = await system.analyze_cluster_quality(clusters)
    print(f"\n📈 Quality Metrics:")
    print(f"  Total clusters: {quality['total_clusters']}")
    print(f"  Average cluster size: {quality['average_cluster_size']}")


if __name__ == "__main__":
    asyncio.run(demo_clustering_system())