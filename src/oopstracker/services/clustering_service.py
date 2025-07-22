"""
Function clustering service for OOPStracker.
Handles function group clustering and analysis.
"""

import logging
from typing import List, Optional, Dict, Any
import asyncio

from ..models import CodeRecord


class ClusteringService:
    """Service for clustering functions into groups."""
    
    def __init__(self, detector, logger: Optional[logging.Logger] = None):
        """Initialize the clustering service.
        
        Args:
            detector: The AST SimHash detector instance
            logger: Optional logger instance
        """
        self.detector = detector
        self.logger = logger or logging.getLogger(__name__)
        self._clustering_system = None
        
    async def _get_clustering_system(self):
        """Lazy load the clustering system."""
        if self._clustering_system is None:
            # Import here to avoid circular imports
            from ..function_group_clustering import FunctionGroupClusteringSystem
            self._clustering_system = FunctionGroupClusteringSystem(enable_ai=True)
        return self._clustering_system
        
    async def cluster_functions(self,
                              enable_clustering: bool = False,
                              clustering_strategy: str = 'category_based',
                              verbose: bool = False,
                              limit: Optional[int] = None) -> Dict[str, Any]:
        """Cluster functions into groups.
        
        Args:
            enable_clustering: Whether to enable clustering
            clustering_strategy: Strategy to use for clustering
            verbose: Show detailed cluster information
            limit: Maximum number of clusters to display
            
        Returns:
            Dictionary containing clustering results
        """
        if not enable_clustering:
            return {
                'enabled': False,
                'clusters': [],
                'total_functions': 0
            }
            
        self.logger.info("Function Group Clustering Analysis")
        
        # Get clustering system
        clustering_system = await self._get_clustering_system()
        
        # Import strategy enum
        from ..function_group_clustering import ClusteringStrategy
        
        # Convert strategy string to enum
        strategy_map = {
            'category_based': ClusteringStrategy.CATEGORY_BASED,
            'semantic_similarity': ClusteringStrategy.SEMANTIC_SIMILARITY,
            'hybrid': ClusteringStrategy.HYBRID
        }
        strategy = strategy_map.get(clustering_strategy, ClusteringStrategy.CATEGORY_BASED)
        
        # Load functions from detector
        all_functions = await clustering_system.load_all_functions_from_repository(
            list(self.detector.code_units.values())
        )
        
        if not all_functions:
            return {
                'enabled': True,
                'clusters': [],
                'total_functions': 0,
                'strategy': clustering_strategy
            }
            
        self.logger.info(
            f"Clustering {len(all_functions)} functions using {clustering_strategy} strategy..."
        )
        
        # Create clusters
        clusters = await clustering_system.get_current_function_clusters(all_functions, strategy)
        
        # Sort clusters by size (descending)
        sorted_clusters = sorted(clusters, key=lambda c: len(c.functions), reverse=True)
        
        # Apply limit if specified
        display_clusters = sorted_clusters[:limit] if limit else sorted_clusters
        
        return {
            'enabled': True,
            'clusters': display_clusters,
            'all_clusters': sorted_clusters,
            'total_functions': len(all_functions),
            'total_clusters': len(clusters),
            'strategy': clustering_strategy,
            'verbose': verbose
        }
        
    def format_clustering_results(self, results: Dict[str, Any]) -> str:
        """Format clustering results for display.
        
        Args:
            results: Clustering results dictionary
            
        Returns:
            Formatted string for display
        """
        if not results['enabled']:
            return ""
            
        lines = [f"\n🔬 Function Group Clustering Analysis"]
        
        if results['total_functions'] == 0:
            lines.append("   No functions found for clustering")
            return "\n".join(lines)
            
        lines.append(f"\n   📊 Clustering Results:")
        lines.append(f"   Total functions: {results['total_functions']}")
        lines.append(f"   Total clusters: {results['total_clusters']}")
        lines.append(f"   Strategy: {results['strategy']}")
        
        # Show clusters
        display_clusters = results['clusters']
        
        if display_clusters:
            lines.append(f"\n   📋 Top {len(display_clusters)} Clusters:")
            
            for i, cluster in enumerate(display_clusters, 1):
                lines.append(f"\n   {i}. {cluster.name} ({len(cluster.functions)} functions)")
                lines.append(f"      Primary patterns: {', '.join(cluster.primary_patterns[:3])}")
                
                if cluster.risk_level != "low":
                    lines.append(f"      ⚠️  Risk level: {cluster.risk_level}")
                
                if results.get('verbose') and cluster.functions:
                    # Show first few functions in cluster
                    lines.append("      Functions:")
                    for func in cluster.functions[:5]:
                        lines.append(f"         - {func.name} ({func.file_path})")
                    if len(cluster.functions) > 5:
                        lines.append(f"         ... and {len(cluster.functions) - 5} more")
                        
        # Show tips
        if results['total_clusters'] > len(display_clusters):
            remaining = results['total_clusters'] - len(display_clusters)
            lines.append(f"\n   ... and {remaining} more clusters")
            
        if not results.get('verbose'):
            lines.append("\n   💡 Use --verbose to see functions in each cluster")
            
        return "\n".join(lines)
        
    async def get_cluster_insights(self, clusters: List[Any]) -> Dict[str, Any]:
        """Get insights about the clusters.
        
        Args:
            clusters: List of function clusters
            
        Returns:
            Dictionary containing cluster insights
        """
        insights = {
            'total_clusters': len(clusters),
            'risk_distribution': {'low': 0, 'medium': 0, 'high': 0},
            'largest_cluster_size': 0,
            'average_cluster_size': 0,
            'pattern_frequency': {}
        }
        
        if not clusters:
            return insights
            
        total_functions = 0
        
        for cluster in clusters:
            # Risk distribution
            insights['risk_distribution'][cluster.risk_level] += 1
            
            # Cluster sizes
            cluster_size = len(cluster.functions)
            total_functions += cluster_size
            insights['largest_cluster_size'] = max(
                insights['largest_cluster_size'], 
                cluster_size
            )
            
            # Pattern frequency
            for pattern in cluster.primary_patterns:
                insights['pattern_frequency'][pattern] = \
                    insights['pattern_frequency'].get(pattern, 0) + 1
                    
        insights['average_cluster_size'] = total_functions / len(clusters)
        
        return insights