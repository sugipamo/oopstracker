"""
Graph construction layer for AST SimHash detector.
Handles building similarity graphs with various strategies.
"""

import logging
from typing import Dict, List, Tuple

from ..detectors import SimilarityGraphBuilder, AdaptiveThresholdFinder
from ..ast_analyzer import ASTAnalyzer

logger = logging.getLogger(__name__)


class GraphConstructionLayer:
    """Handles similarity graph construction and analysis."""
    
    def __init__(self):
        """Initialize graph construction layer."""
        self.analyzer = ASTAnalyzer()
        self.graph_builder = SimilarityGraphBuilder(self.analyzer)
        self.adaptive_threshold_finder = AdaptiveThresholdFinder(self.graph_builder)
        
    def build_similarity_graph(self, data_layer, threshold: float = 0.3, 
                               use_fast_mode: bool = True) -> Dict[str, List[Tuple[str, float]]]:
        """
        Build a similarity graph where nodes are code units and edges represent similarity.
        
        Args:
            data_layer: Data management layer instance
            threshold: Minimum similarity to create an edge
            use_fast_mode: Use SimHash pre-filtering for speed
            
        Returns:
            Graph as adjacency list: {node_hash: [(neighbor_hash, similarity), ...]}
        """
        records = data_layer.get_all_records()
        
        if use_fast_mode:
            return self.graph_builder.build_similarity_graph_fast(
                records, data_layer.code_units, data_layer.bk_tree, threshold
            )
        else:
            return self.graph_builder.build_similarity_graph_full(
                records, data_layer.code_units, threshold
            )
    
    def find_relations_adaptive(self, data_layer, 
                                target_connections: int = 200, 
                                max_connections: int = 1000,
                                min_threshold: float = 0.1, 
                                max_threshold: float = 0.9,
                                use_fast_mode: bool = True) -> Tuple[Dict[str, List[Tuple[str, float]]], float]:
        """
        Build similarity graph with adaptive threshold to achieve target connectivity.
        
        Args:
            data_layer: Data management layer instance
            target_connections: Target number of total connections
            max_connections: Maximum allowed connections
            min_threshold: Minimum similarity threshold to try
            max_threshold: Maximum similarity threshold to try
            use_fast_mode: Use fast mode for graph building
            
        Returns:
            Tuple of (graph, selected_threshold)
        """
        records = data_layer.get_all_records()
        return self.adaptive_threshold_finder.find_adaptive_threshold(
            records, data_layer.code_units, data_layer.bk_tree,
            target_connections, max_connections,
            min_threshold, max_threshold, use_fast_mode
        )
    
    def analyze_graph_components(self, graph: Dict[str, List[Tuple[str, float]]]) -> Dict[str, any]:
        """
        Analyze graph structure to find connected components.
        
        Args:
            graph: Similarity graph as adjacency list
            
        Returns:
            Dictionary with component analysis
        """
        # Find connected components
        visited = set()
        components = []
        
        for node in graph:
            if node not in visited:
                component = self._dfs_component(node, graph, visited)
                components.append(component)
        
        # Analyze components
        component_sizes = [len(c) for c in components]
        
        return {
            'total_nodes': len(graph),
            'total_edges': sum(len(neighbors) for neighbors in graph.values()) // 2,
            'num_components': len(components),
            'component_sizes': component_sizes,
            'largest_component': max(component_sizes) if component_sizes else 0,
            'isolated_nodes': sum(1 for c in components if len(c) == 1),
            'avg_component_size': sum(component_sizes) / len(components) if components else 0
        }
    
    def _dfs_component(self, start: str, graph: Dict[str, List[Tuple[str, float]]], 
                       visited: set) -> List[str]:
        """DFS to find connected component."""
        stack = [start]
        component = []
        
        while stack:
            node = stack.pop()
            if node not in visited:
                visited.add(node)
                component.append(node)
                
                # Add neighbors to stack
                if node in graph:
                    for neighbor, _ in graph[node]:
                        if neighbor not in visited:
                            stack.append(neighbor)
        
        return component
    
    def find_clusters(self, graph: Dict[str, List[Tuple[str, float]]], 
                      min_cluster_size: int = 3) -> List[List[str]]:
        """
        Find dense clusters in the similarity graph.
        
        Args:
            graph: Similarity graph
            min_cluster_size: Minimum size for a cluster
            
        Returns:
            List of clusters (each cluster is a list of node hashes)
        """
        # Simple clustering based on high connectivity
        clusters = []
        visited = set()
        
        # Sort nodes by degree (number of connections)
        node_degrees = [(node, len(neighbors)) for node, neighbors in graph.items()]
        node_degrees.sort(key=lambda x: x[1], reverse=True)
        
        for node, degree in node_degrees:
            if node in visited or degree < min_cluster_size - 1:
                continue
            
            # Build cluster around high-degree node
            cluster = self._build_cluster(node, graph, visited)
            
            if len(cluster) >= min_cluster_size:
                clusters.append(cluster)
        
        return clusters
    
    def _build_cluster(self, seed: str, graph: Dict[str, List[Tuple[str, float]]], 
                       visited: set) -> List[str]:
        """Build a cluster starting from a seed node."""
        cluster = [seed]
        visited.add(seed)
        
        # Get all neighbors of seed
        if seed in graph:
            neighbors = [n for n, _ in graph[seed] if n not in visited]
            
            # Add neighbors that are well-connected to the cluster
            for neighbor in neighbors:
                if neighbor in graph:
                    # Check connectivity to existing cluster members
                    connections_to_cluster = sum(
                        1 for member in cluster 
                        if any(n == member for n, _ in graph.get(neighbor, []))
                    )
                    
                    # Add if well-connected to cluster
                    if connections_to_cluster >= len(cluster) * 0.5:
                        cluster.append(neighbor)
                        visited.add(neighbor)
        
        return cluster