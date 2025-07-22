"""
Similarity graph builder for AST SimHash detector.

This module builds relationship graphs between similar code units
for visualization and analysis.
"""

import logging
import random
from typing import Dict, List, Tuple, Optional
from ..models import CodeRecord
from ..ast_analyzer import ASTAnalyzer, CodeUnit
from ..simhash_detector import BKTree
from ..progress_reporter import ProgressReporter

logger = logging.getLogger(__name__)


class SimilarityGraphBuilder:
    """Builds similarity graphs between code units."""
    
    def __init__(self, analyzer: ASTAnalyzer):
        """
        Initialize graph builder.
        
        Args:
            analyzer: AST analyzer instance
        """
        self.analyzer = analyzer
    
    def build_similarity_graph_fast(
        self,
        records: List[CodeRecord],
        code_units: dict,
        bk_tree: BKTree,
        threshold: float = 0.3
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Build similarity graph using fast SimHash search.
        
        Args:
            records: List of code records
            code_units: Mapping of hash to CodeUnit
            bk_tree: BK-tree for SimHash search
            threshold: Minimum similarity threshold
            
        Returns:
            Graph as adjacency list: {node_hash: [(neighbor_hash, similarity), ...]}
        """
        graph = {}
        
        # Determine appropriate hamming distance for threshold
        # Lower similarity threshold allows more distant matches
        hamming_threshold = max(10, int(64 * (1.0 - threshold)))
        
        logger.info(f"Building fast similarity graph with threshold {threshold}, hamming distance {hamming_threshold}")
        
        # Create progress reporter
        progress_reporter = ProgressReporter(
            interval_seconds=5.0,
            min_items_for_display=100
        )
        
        total_records = len(records)
        
        for i, record in enumerate(records):
            progress_reporter.print_progress(i + 1, total_records, unit="nodes")
            
            unit = code_units.get(record.code_hash)
            if not unit or record.simhash is None:
                continue
            
            # Find similar records using BK-tree
            similar_tuples = bk_tree.search(record.simhash, hamming_threshold)
            
            # Build edges
            edges = []
            for similar_record, hamming_dist in similar_tuples:
                if similar_record.code_hash == record.code_hash:
                    continue
                
                similar_unit = code_units.get(similar_record.code_hash)
                if not similar_unit:
                    continue
                
                # Calculate actual similarity
                similarity = self.analyzer.calculate_structural_similarity(unit, similar_unit)
                
                if similarity >= threshold:
                    edges.append((similar_record.code_hash, similarity))
            
            # Sort edges by similarity
            edges.sort(key=lambda x: x[1], reverse=True)
            
            # Store in graph
            if edges:
                graph[record.code_hash] = edges
        
        logger.info(f"Built similarity graph with {len(graph)} nodes and {sum(len(edges) for edges in graph.values())} edges")
        return graph
    
    def build_similarity_graph_full(
        self,
        records: List[CodeRecord],
        code_units: dict,
        threshold: float = 0.3
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Build complete similarity graph with exhaustive comparison.
        
        Args:
            records: List of code records
            code_units: Mapping of hash to CodeUnit
            threshold: Minimum similarity threshold
            
        Returns:
            Graph as adjacency list: {node_hash: [(neighbor_hash, similarity), ...]}
        """
        graph = {}
        
        logger.info(f"Building full similarity graph with threshold {threshold}")
        
        # Create progress reporter
        progress_reporter = ProgressReporter(
            interval_seconds=5.0,
            min_items_for_display=100
        )
        
        total_comparisons = len(records) * (len(records) - 1) // 2
        comparison_count = 0
        
        for i, record1 in enumerate(records):
            unit1 = code_units.get(record1.code_hash)
            if not unit1:
                continue
            
            edges = []
            
            for j, record2 in enumerate(records[i+1:], i+1):
                comparison_count += 1
                progress_reporter.print_progress(comparison_count, total_comparisons, unit="comparisons")
                
                unit2 = code_units.get(record2.code_hash)
                if not unit2:
                    continue
                
                # Calculate similarity
                similarity = self.analyzer.calculate_structural_similarity(unit1, unit2)
                
                if similarity >= threshold:
                    # Add edge in both directions
                    edges.append((record2.code_hash, similarity))
                    
                    # Also add reverse edge
                    if record2.code_hash not in graph:
                        graph[record2.code_hash] = []
                    graph[record2.code_hash].append((record1.code_hash, similarity))
            
            # Sort edges by similarity
            if edges:
                edges.sort(key=lambda x: x[1], reverse=True)
                
                if record1.code_hash in graph:
                    graph[record1.code_hash].extend(edges)
                else:
                    graph[record1.code_hash] = edges
        
        # Sort all edge lists
        for node in graph:
            graph[node].sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Built full similarity graph with {len(graph)} nodes and {sum(len(edges) for edges in graph.values())} edges")
        return graph
    
    def build_sample_graph(
        self,
        sample_records: List[CodeRecord],
        code_units: dict,
        threshold: float
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Build similarity graph for a sample of records.
        
        Args:
            sample_records: Sample of code records
            code_units: Mapping of hash to CodeUnit
            threshold: Minimum similarity threshold
            
        Returns:
            Graph as adjacency list
        """
        graph = {}
        
        for i, record1 in enumerate(sample_records):
            unit1 = code_units.get(record1.code_hash)
            if not unit1:
                continue
            
            edges = []
            
            for j, record2 in enumerate(sample_records):
                if i == j:
                    continue
                
                unit2 = code_units.get(record2.code_hash)
                if not unit2:
                    continue
                
                # Calculate similarity
                similarity = self.analyzer.calculate_structural_similarity(unit1, unit2)
                
                if similarity >= threshold:
                    edges.append((record2.code_hash, similarity))
            
            # Sort and store edges
            if edges:
                edges.sort(key=lambda x: x[1], reverse=True)
                graph[record1.code_hash] = edges
        
        return graph