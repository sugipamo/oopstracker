"""
Adaptive threshold finder for similarity detection.

This module handles dynamic threshold adjustment to achieve target connectivity.
"""

import logging
import random
from typing import Dict, List, Tuple, Optional

from ..models import CodeRecord
from ..ast_analyzer import CodeUnit
from .graph_builder import SimilarityGraphBuilder

logger = logging.getLogger(__name__)


class AdaptiveThresholdFinder:
    """Find optimal similarity threshold to achieve target connectivity."""
    
    def __init__(self, graph_builder: SimilarityGraphBuilder):
        """
        Initialize adaptive threshold finder.
        
        Args:
            graph_builder: Graph builder instance for constructing similarity graphs
        """
        self.graph_builder = graph_builder
    
    def find_adaptive_threshold(
        self, 
        records: List[CodeRecord],
        code_units: Dict[str, CodeUnit],
        bk_tree,
        target_connections: int = 200,
        max_connections: int = 1000,
        min_threshold: float = 0.1,
        max_threshold: float = 0.9,
        use_fast_mode: bool = True
    ) -> Tuple[Dict[str, List[Tuple[str, float]]], float]:
        """
        Find optimal threshold using binary search to achieve target connectivity.
        
        Args:
            records: List of code records
            code_units: Mapping of hash to CodeUnit
            bk_tree: BK-tree for fast similarity search
            target_connections: Target number of connections
            max_connections: Maximum allowed connections
            min_threshold: Minimum threshold to try
            max_threshold: Maximum threshold to try
            use_fast_mode: Use fast mode for graph building
            
        Returns:
            Tuple of (graph, selected_threshold)
        """
        logger.info(f"Building adaptive similarity graph targeting {target_connections} connections")
        
        # Binary search for optimal threshold
        low, high = min_threshold, max_threshold
        best_graph = {}
        best_threshold = (low + high) / 2
        best_diff = float('inf')
        
        # First, try with a small sample to estimate
        sample_size = min(100, len(records))
        
        if sample_size < 10:
            # Too few records, just use middle threshold
            logger.warning(f"Too few records ({len(records)}) for adaptive threshold")
            if use_fast_mode:
                graph = self.graph_builder.build_similarity_graph_fast(
                    records, code_units, bk_tree, best_threshold
                )
            else:
                graph = self.graph_builder.build_similarity_graph_full(
                    records, code_units, best_threshold
                )
            return graph, best_threshold
        
        sample_records = random.sample(records, sample_size)
        
        iterations = 0
        max_iterations = 10
        
        while low <= high and iterations < max_iterations:
            iterations += 1
            mid_threshold = (low + high) / 2
            
            # Build sample graph
            sample_graph = self.graph_builder.build_sample_graph(
                sample_records, code_units, mid_threshold
            )
            
            # Estimate total connections
            sample_connections = sum(len(edges) for edges in sample_graph.values())
            estimated_total = sample_connections * (len(records) / sample_size) ** 2
            
            logger.info(f"Iteration {iterations}: threshold={mid_threshold:.3f}, "
                        f"sample_connections={sample_connections}, "
                        f"estimated_total={estimated_total:.0f}")
            
            diff = abs(estimated_total - target_connections)
            
            if diff < best_diff:
                best_diff = diff
                best_threshold = mid_threshold
            
            if estimated_total < target_connections * 0.9:
                # Need more connections, lower threshold
                high = mid_threshold - 0.01
            elif estimated_total > max_connections:
                # Too many connections, raise threshold
                low = mid_threshold + 0.01
            else:
                # Close enough
                break
        
        # Build final graph with selected threshold
        logger.info(f"Selected threshold: {best_threshold:.3f}")
        
        if use_fast_mode:
            best_graph = self.graph_builder.build_similarity_graph_fast(
                records, code_units, bk_tree, best_threshold
            )
        else:
            best_graph = self.graph_builder.build_similarity_graph_full(
                records, code_units, best_threshold
            )
        
        actual_connections = sum(len(edges) for edges in best_graph.values())
        logger.info(f"Final graph: {len(best_graph)} nodes, {actual_connections} connections")
        
        return best_graph, best_threshold