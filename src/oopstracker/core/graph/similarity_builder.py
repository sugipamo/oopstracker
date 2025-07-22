"""
Similarity graph building functionality.
"""

import logging
from typing import Dict, List, Tuple

from ...models import CodeRecord
from ...ast_analyzer import ASTAnalyzer, CodeUnit
from ...progress_reporter import ProgressReporter
from ..simhash import SimHashCalculator

logger = logging.getLogger(__name__)


class SimilarityGraphBuilder:
    """
    Builds similarity graphs between code units.
    """
    
    def __init__(self, simhash_calculator: SimHashCalculator, analyzer: ASTAnalyzer):
        """
        Initialize graph builder.
        
        Args:
            simhash_calculator: SimHash calculator instance
            analyzer: AST analyzer for structural similarity
        """
        self.simhash_calculator = simhash_calculator
        self.analyzer = analyzer
        
    def build_similarity_graph(self, threshold: float = 0.3, 
                             use_fast_mode: bool = True) -> Dict[str, List[Tuple[str, float]]]:
        """
        Build a similarity graph showing relationships between all code units.
        
        Args:
            threshold: Minimum similarity threshold for connections
            use_fast_mode: Use SimHash filtering for faster computation
            
        Returns:
            Dictionary mapping code_hash to list of (connected_hash, similarity) tuples
        """
        if use_fast_mode:
            return self._build_similarity_graph_fast(threshold)
        else:
            return self._build_similarity_graph_full(threshold)
            
    def _build_similarity_graph_fast(self, threshold: float = 0.3) -> Dict[str, List[Tuple[str, float]]]:
        """
        Fast similarity graph using SimHash pre-filtering.
        Reduces computation from O(n²) to approximately O(n log n).
        """
        logger.info(f"Building similarity graph (FAST mode) with threshold {threshold}")
        
        graph = {}
        records = self.simhash_calculator.get_all_records()
        
        # Initialize graph nodes
        for record in records:
            graph[record.code_hash] = []
        
        # Convert structural similarity threshold to approximate Hamming distance
        hamming_threshold = max(5, int((1.0 - threshold) * 25))
        logger.debug(f"Using Hamming threshold {hamming_threshold} for similarity {threshold}")
        
        # Process each record
        for record1 in records:
            unit1 = self.simhash_calculator.get_code_unit(record1.code_hash)
            if not unit1:
                continue
                
            # Find similar records by SimHash
            similar_hashes = self.simhash_calculator.find_similar_hashes(
                record1.code_hash, hamming_threshold
            )
            
            for hash2 in similar_hashes:
                if hash2 == record1.code_hash:
                    continue
                    
                record2 = self.simhash_calculator.get_record(hash2)
                unit2 = self.simhash_calculator.get_code_unit(hash2)
                
                if not record2 or not unit2:
                    continue
                
                # Skip if same location
                if (unit1.file_path == unit2.file_path and 
                    unit1.type == unit2.type and 
                    unit1.name == unit2.name):
                    continue
                
                # Calculate structural similarity
                similarity = self.analyzer.calculate_structural_similarity(unit1, unit2)
                
                if similarity >= threshold:
                    # Add connection (avoid duplicates)
                    if not any(h == hash2 for h, _ in graph[record1.code_hash]):
                        graph[record1.code_hash].append((hash2, similarity))
        
        # Sort connections by similarity
        for code_hash in graph:
            graph[code_hash].sort(key=lambda x: x[1], reverse=True)
        
        total_connections = sum(len(connections) for connections in graph.values())
        logger.info(f"Fast mode: found {total_connections} connections")
        
        return graph
        
    def _build_similarity_graph_full(self, threshold: float = 0.3) -> Dict[str, List[Tuple[str, float]]]:
        """
        Full O(n²) similarity graph computation.
        Use only for small datasets or when maximum accuracy is needed.
        """
        logger.info(f"Building similarity graph (FULL mode) with threshold {threshold}")
        logger.warning("Full mode is O(n²) - may be slow for large datasets")
        
        graph = {}
        records = self.simhash_calculator.get_all_records()
        
        # Initialize graph nodes
        for record in records:
            graph[record.code_hash] = []
        
        # Build connections - O(n²)
        total_pairs = len(records) * (len(records) - 1) // 2
        processed = 0
        
        # Create progress reporter
        progress_reporter = ProgressReporter(
            interval_seconds=5.0,
            min_items_for_display=1000,
            silent=False
        )
        
        for i, record1 in enumerate(records):
            unit1 = self.simhash_calculator.get_code_unit(record1.code_hash)
            if not unit1:
                continue
            
            for j, record2 in enumerate(records[i+1:], i+1):
                unit2 = self.simhash_calculator.get_code_unit(record2.code_hash)
                if not unit2:
                    continue
                
                processed += 1
                progress_reporter.print_progress(processed, total_pairs, unit="pairs")
                
                # Skip if same location
                if (unit1.file_path == unit2.file_path and 
                    unit1.type == unit2.type and 
                    unit1.name == unit2.name):
                    continue
                
                similarity = self.analyzer.calculate_structural_similarity(unit1, unit2)
                
                if similarity >= threshold:
                    # Add bidirectional connection
                    graph[record1.code_hash].append((record2.code_hash, similarity))
                    graph[record2.code_hash].append((record1.code_hash, similarity))
        
        # Sort connections by similarity
        for code_hash in graph:
            graph[code_hash].sort(key=lambda x: x[1], reverse=True)
        
        total_connections = sum(len(connections) for connections in graph.values()) // 2
        logger.info(f"Full mode: processed {processed} pairs, found {total_connections} connections")
        
        return graph
        
    def get_related_units(self, code_hash: str, threshold: float = 0.3, 
                         max_results: int = 10) -> List[Tuple[CodeRecord, float]]:
        """
        Get units related to a specific code unit.
        
        Args:
            code_hash: Hash of the target unit
            threshold: Minimum similarity threshold
            max_results: Maximum number of results to return
            
        Returns:
            List of (record, similarity) tuples
        """
        target_record = self.simhash_calculator.get_record(code_hash)
        target_unit = self.simhash_calculator.get_code_unit(code_hash)
        
        if not target_record or not target_unit:
            logger.warning(f"Code unit not found: {code_hash}")
            return []
        
        related = []
        
        # Find similar hashes
        hamming_threshold = max(5, int((1.0 - threshold) * 25))
        similar_hashes = self.simhash_calculator.find_similar_hashes(
            code_hash, hamming_threshold
        )
        
        for hash_value in similar_hashes:
            if hash_value == code_hash:
                continue
                
            record = self.simhash_calculator.get_record(hash_value)
            unit = self.simhash_calculator.get_code_unit(hash_value)
            
            if record and unit:
                similarity = self.analyzer.calculate_structural_similarity(target_unit, unit)
                if similarity >= threshold:
                    related.append((record, similarity))
        
        # Sort by similarity and limit results
        related.sort(key=lambda x: x[1], reverse=True)
        return related[:max_results]
        
    def find_relations_adaptive(self, target_connections: int = 200, 
                              max_connections: int = 1000,
                              initial_threshold: float = 0.7) -> Dict[str, List[Tuple[str, float]]]:
        """
        Build a similarity graph with adaptive threshold adjustment.
        
        Args:
            target_connections: Target number of total connections
            max_connections: Maximum allowed connections
            initial_threshold: Starting similarity threshold
            
        Returns:
            Similarity graph
        """
        logger.info(f"Building adaptive similarity graph (target: {target_connections} connections)")
        
        threshold = initial_threshold
        graph = None
        attempts = 0
        max_attempts = 10
        
        while attempts < max_attempts:
            attempts += 1
            
            # Build graph with current threshold
            graph = self.build_similarity_graph(threshold, use_fast_mode=True)
            
            # Count connections
            total_connections = sum(len(connections) for connections in graph.values()) // 2
            
            logger.info(f"Attempt {attempts}: threshold={threshold:.2f}, connections={total_connections}")
            
            # Check if we're in acceptable range
            if target_connections * 0.8 <= total_connections <= max_connections:
                logger.info(f"Found acceptable graph with {total_connections} connections")
                break
            
            # Adjust threshold
            if total_connections < target_connections * 0.8:
                # Too few connections, lower threshold
                threshold *= 0.85
            else:
                # Too many connections, raise threshold
                threshold = min(0.95, threshold * 1.15)
                
            # Bounds check
            if threshold < 0.1:
                logger.warning("Threshold too low, stopping")
                break
            elif threshold > 0.95:
                logger.warning("Threshold too high, stopping")
                break
        
        return graph or {}