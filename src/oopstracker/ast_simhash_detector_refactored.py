"""
AST-based SimHash duplicate detection (Refactored Version).
Uses structural analysis instead of text-based comparison.

This refactored version separates concerns into specialized components.
"""

import logging
import random
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from .ast_analyzer import ASTAnalyzer, CodeUnit
from .models import CodeRecord, SimilarityResult
from .simhash_detector import BKTree
from .ast_database import ASTDatabaseManager
from .trivial_filter import TrivialPatternFilter, TrivialFilterConfig
from .progress_reporter import ProgressReporter
from .code_filter_utility import CodeFilterUtility
from .detectors import (SimilarityDetector, SimilarityGraphBuilder, DetectorCacheManager,
                        AdaptiveThresholdFinder, StatisticsCollector, TopPercentDuplicateFinder)

logger = logging.getLogger(__name__)


class ASTSimHashDetectorRefactored:
    """
    AST-based SimHash detector for structural code similarity.
    
    This refactored version delegates specific responsibilities to:
    - SimilarityDetector: Core duplicate detection logic
    - SimilarityGraphBuilder: Graph construction
    - DetectorCacheManager: Caching mechanism
    - ASTDatabaseManager: Data persistence
    - AdaptiveThresholdFinder: Dynamic threshold adjustment
    - StatisticsCollector: Code statistics collection
    - TopPercentDuplicateFinder: Top N% duplicate finding
    """
    
    def __init__(self, hamming_threshold: int = 10, db_path: str = "oopstracker_ast.db", include_tests: bool = False):
        """
        Initialize AST SimHash detector.
        
        Args:
            hamming_threshold: Maximum Hamming distance for similarity
            db_path: Path to SQLite database for persistence
            include_tests: Whether to include test functions in analysis (default: False)
        """
        self.hamming_threshold = hamming_threshold
        self.analyzer = ASTAnalyzer()
        self.bk_tree = BKTree()
        self.code_units: Dict[str, CodeUnit] = {}  # hash -> CodeUnit
        self.records: Dict[str, CodeRecord] = {}   # hash -> CodeRecord
        
        # Initialize database
        self.db_manager = ASTDatabaseManager(db_path)
        
        # Initialize trivial pattern filter (keep for compatibility)
        self.trivial_filter = TrivialPatternFilter(TrivialFilterConfig(), include_tests=include_tests)
        
        # Initialize unified code filter utility
        self.code_filter = CodeFilterUtility(include_tests=include_tests, include_trivial=False)
        
        # Initialize components for separated concerns
        self.similarity_detector = SimilarityDetector(self.analyzer, self.code_filter)
        self.graph_builder = SimilarityGraphBuilder(self.analyzer)
        self.cache_manager = DetectorCacheManager()
        self.adaptive_threshold_finder = AdaptiveThresholdFinder(self.graph_builder)
        self.statistics_collector = StatisticsCollector()
        self.top_percent_finder = TopPercentDuplicateFinder(self.similarity_detector, self.hamming_threshold)
        
        # Load existing data
        self._load_existing_data()
        
        logger.info(f"Initialized AST SimHash detector with threshold {hamming_threshold}, loaded {len(self.records)} existing records")
    
    def _load_existing_data(self):
        """
        Load existing data from database into memory structures.
        Only loads records from files that currently exist.
        """
        try:
            # First, get list of all files in the database
            existing_files = self.db_manager.get_existing_files()
            
            # Filter to only files that still exist
            valid_files = set()
            for file_path in existing_files:
                if Path(file_path).exists():
                    valid_files.add(file_path)
            
            logger.info(f"Found {len(valid_files)} existing files out of {len(existing_files)} tracked files")
            
            # Load all records
            existing_data = self.db_manager.get_all_records()
            loaded_count = 0
            skipped_count = 0
            
            for record, unit in existing_data:
                # Only load if file still exists
                if record.file_path and record.file_path in valid_files:
                    # Store in memory
                    self.records[record.code_hash] = record
                    self.code_units[record.code_hash] = unit
                    
                    # Rebuild BK-tree
                    if record.simhash is not None:
                        self.bk_tree.insert(record.simhash, record)
                    
                    loaded_count += 1
                else:
                    skipped_count += 1
            
            logger.info(f"Loaded {loaded_count} records from existing files, skipped {skipped_count} from deleted files")
            
        except Exception as e:
            logger.error(f"Failed to load existing data: {e}")
    
    def register_file(self, file_path: str, force: bool = False) -> List[CodeRecord]:
        """
        Register all functions and classes from a Python file.
        
        Args:
            file_path: Path to Python file
            force: Force re-registration even if already registered
            
        Returns:
            List of registered CodeRecord objects
        """
        logger.info(f"Registering file: {file_path}")
        
        # Check if file has been modified since last registration
        if not force:
            existing_records = self.db_manager.get_file_records(file_path)
            if existing_records:
                file_mtime = Path(file_path).stat().st_mtime
                # Check if any record is newer than file
                if any(record.timestamp >= file_mtime for record in existing_records):
                    logger.info(f"File {file_path} already up to date")
                    return existing_records
        
        # Remove old records for this file
        self.db_manager.remove_file(file_path)
        
        # Also remove from memory
        to_remove = [hash for hash, record in self.records.items() 
                     if record.file_path == file_path]
        for hash in to_remove:
            self.records.pop(hash, None)
            self.code_units.pop(hash, None)
        
        # Extract and register code units
        units = self.analyzer.extract_code_units(file_path)
        
        if not units:
            logger.warning(f"No code units found in {file_path}")
            return []
        
        registered = []
        for unit in units:
            record = self._register_unit(unit)
            if record:
                registered.append(record)
        
        logger.info(f"Registered {len(registered)} code units from {file_path}")
        return registered
    
    def register_code(self, source_code: str, function_name: Optional[str] = None,
                      file_path: Optional[str] = None) -> Optional[CodeRecord]:
        """
        Register a single piece of code.
        
        Args:
            source_code: Python source code
            function_name: Optional function/class name
            file_path: Optional file path
            
        Returns:
            CodeRecord if registered successfully
        """
        units = self.analyzer.extract_units_from_source(source_code)
        
        # If function_name specified, find that specific unit
        if function_name:
            for unit in units:
                if unit.name == function_name:
                    return self._register_unit(unit)
            logger.warning(f"Function '{function_name}' not found in source")
            return None
        
        # Otherwise register first unit
        if units:
            return self._register_unit(units[0])
        
        return None
    
    def _register_unit(self, unit: CodeUnit) -> Optional[CodeRecord]:
        """Register a single code unit."""
        # Check if this exact code already exists
        existing_record = self.records.get(unit.code_hash)
        if existing_record:
            logger.debug(f"Code unit already registered: {unit.name}")
            return existing_record
        
        # Calculate SimHash
        simhash = self.analyzer.calculate_simhash(unit)
        
        # Create record
        record = CodeRecord(
            code_hash=unit.code_hash,
            function_name=unit.name,
            file_path=unit.file_path,
            start_line=unit.start_line,
            end_line=unit.end_line,
            code_type=unit.unit_type,
            simhash=simhash,
            ast_hash=unit.ast_hash,
            semantic_hash=unit.semantic_hash,
            intent_category=unit.intent_category,
            code_snippet=unit.source[:200] + "..." if len(unit.source) > 200 else unit.source
        )
        
        # Store in memory
        self.records[record.code_hash] = record
        self.code_units[record.code_hash] = unit
        
        # Add to BK-tree
        if simhash is not None:
            self.bk_tree.insert(simhash, record)
        
        # Persist to database
        try:
            self.db_manager.add_record(record, unit)
        except Exception as e:
            logger.error(f"Failed to persist record: {e}")
        
        return record
    
    def find_similar(self, source_code: str, function_name: Optional[str] = None,
                     threshold: float = 0.7) -> SimilarityResult:
        """
        Find similar code to the given source.
        
        Args:
            source_code: Python source code to compare
            function_name: Optional specific function to extract
            threshold: Minimum similarity threshold
            
        Returns:
            SimilarityResult with similar code units
        """
        # Extract target unit
        units = self.analyzer.extract_units_from_source(source_code)
        if not units:
            return SimilarityResult(similar_units=[])
        
        # Find specific function if requested
        target_unit = None
        if function_name:
            for unit in units:
                if unit.name == function_name:
                    target_unit = unit
                    break
        else:
            target_unit = units[0]
        
        if not target_unit:
            return SimilarityResult(similar_units=[])
        
        return self._find_similar_unit(target_unit)
    
    def _find_similar_unit(self, target_unit: CodeUnit) -> SimilarityResult:
        """Find units similar to the given target unit."""
        # Calculate SimHash for target
        target_simhash = self.analyzer.calculate_simhash(target_unit)
        
        similar_units = []
        
        if target_simhash is not None:
            # Use BK-tree to find candidates
            candidates = self.bk_tree.search(target_simhash, self.hamming_threshold)
            
            for record, hamming_distance in candidates:
                unit = self.code_units.get(record.code_hash)
                if not unit:
                    continue
                
                # Calculate detailed similarity
                similarity = self.analyzer.calculate_structural_similarity(target_unit, unit)
                
                similar_units.append({
                    'record': record,
                    'unit': unit,
                    'similarity': similarity,
                    'hamming_distance': hamming_distance
                })
        
        # Sort by similarity
        similar_units.sort(key=lambda x: x['similarity'], reverse=True)
        
        return SimilarityResult(similar_units=similar_units[:10])  # Top 10
    
    def find_potential_duplicates(self, threshold: float = 0.8, use_fast_mode: bool = True, 
                                  use_cache: bool = True, include_trivial: bool = False, 
                                  silent: bool = False, top_percent: Optional[float] = None) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """
        Find potential duplicate pairs across all registered code.
        
        Args:
            threshold: Minimum similarity threshold
            use_fast_mode: Use SimHash for pre-filtering (much faster)
            use_cache: Use cached results if available
            include_trivial: Include trivial duplicates (pass classes, simple getters, etc.)
            silent: If True, suppress progress messages
            top_percent: If provided, dynamically adjust threshold to capture top N% of duplicates
            
        Returns:
            List of (record1, record2, similarity_score) tuples
        """
        # Handle dynamic threshold adjustment for top N%
        if top_percent is not None:
            return self._find_top_percent_duplicates(top_percent, use_fast_mode, include_trivial, silent)
        
        logger.info(f"Searching for potential duplicates with threshold {threshold} (fast_mode: {use_fast_mode}, cache: {use_cache}, include_trivial: {include_trivial})")
        
        # Check cache
        cache_key = self.cache_manager.get_cache_key(threshold, use_fast_mode, include_trivial, len(self.records))
        current_timestamp = max((r.timestamp for r in self.records.values()), default=0)
        
        if use_cache:
            cached_result = self.cache_manager.get_cached_result(cache_key, current_timestamp)
            if cached_result is not None:
                return cached_result
        
        # Compute duplicates
        records = list(self.records.values())
        
        if use_fast_mode:
            duplicates = self.similarity_detector.find_duplicates_fast(
                records, self.code_units, self.bk_tree, threshold, 
                self.hamming_threshold, include_trivial, silent
            )
        else:
            duplicates = self.similarity_detector.find_duplicates_exhaustive(
                records, self.code_units, threshold, include_trivial, silent
            )
        
        # Update cache
        if use_cache:
            self.cache_manager.cache_result(cache_key, duplicates, current_timestamp)
        
        return duplicates
    
    def build_similarity_graph(self, threshold: float = 0.3, use_fast_mode: bool = True) -> Dict[str, List[Tuple[str, float]]]:
        """
        Build a similarity graph where nodes are code units and edges represent similarity.
        
        Args:
            threshold: Minimum similarity to create an edge
            use_fast_mode: Use SimHash pre-filtering for speed
            
        Returns:
            Graph as adjacency list: {node_hash: [(neighbor_hash, similarity), ...]}
        """
        records = list(self.records.values())
        
        if use_fast_mode:
            return self.graph_builder.build_similarity_graph_fast(
                records, self.code_units, self.bk_tree, threshold
            )
        else:
            return self.graph_builder.build_similarity_graph_full(
                records, self.code_units, threshold
            )
    
    def find_relations_adaptive(self, target_connections: int = 200, max_connections: int = 1000, 
                                min_threshold: float = 0.1, max_threshold: float = 0.9, 
                                use_fast_mode: bool = True) -> Tuple[Dict[str, List[Tuple[str, float]]], float]:
        """
        Build similarity graph with adaptive threshold to achieve target connectivity.
        
        Args:
            target_connections: Target number of total connections in graph
            max_connections: Maximum allowed connections
            min_threshold: Minimum similarity threshold to try
            max_threshold: Maximum similarity threshold to try
            use_fast_mode: Use fast mode for graph building
            
        Returns:
            Tuple of (graph, selected_threshold)
        """
        records = list(self.records.values())
        return self.adaptive_threshold_finder.find_adaptive_threshold(
            records, self.code_units, self.bk_tree,
            target_connections, max_connections,
            min_threshold, max_threshold, use_fast_mode
        )
    
    def _find_top_percent_duplicates(self, top_percent: float, use_fast_mode: bool = True, 
                                     include_trivial: bool = False, silent: bool = False) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """
        Find duplicates by dynamically adjusting threshold to capture top N% most similar pairs.
        
        Args:
            top_percent: Percentage of top duplicates to find (0.0 to 100.0)
            use_fast_mode: Use SimHash for pre-filtering
            include_trivial: Include trivial duplicates
            silent: Suppress progress messages
            
        Returns:
            List of (record1, record2, similarity_score) tuples
        """
        records = list(self.records.values())
        return self.top_percent_finder.find_top_percent(
            records, self.code_units, self.bk_tree,
            top_percent, use_fast_mode, include_trivial, silent
        )
    
    def get_statistics(self) -> Dict:
        """Get statistics about registered code."""
        return self.statistics_collector.collect_statistics(
            self.records, self.hamming_threshold
        )
    
    def clear_memory(self):
        """Clear all stored data."""
        # Clear database
        self.db_manager.clear_all()
        
        # Clear memory structures
        self.bk_tree = BKTree()
        self.code_units.clear()
        self.records.clear()
        
        # Clear cache
        self.cache_manager.clear_cache()
        
        logger.info("Cleared AST SimHash detector memory and database")
    
    def get_all_records(self) -> List[CodeRecord]:
        """
        Get all registered records.
        
        Returns:
            List of all CodeRecord objects
        """
        return list(self.records.values())
    
    def analyze_code_structure(self, source_code: str, file_path: Optional[str] = None) -> Dict:
        """
        Analyze the structure of given source code.
        
        Args:
            source_code: Python source code to analyze
            file_path: Optional file path for context
            
        Returns:
            Dictionary with analysis results
        """
        units = self.analyzer.extract_units_from_source(source_code)
        
        return {
            "total_units": len(units),
            "units": [
                {
                    "name": unit.name,
                    "type": unit.unit_type,
                    "start_line": unit.start_line,
                    "end_line": unit.end_line,
                    "complexity": unit.complexity,
                    "intent_category": unit.intent_category,
                    "metrics": {
                        "lines": unit.end_line - unit.start_line + 1,
                        "ast_nodes": len(unit.ast_nodes) if hasattr(unit, 'ast_nodes') else 0,
                        "variables": len(unit.variables) if hasattr(unit, 'variables') else 0,
                        "calls": len(unit.calls) if hasattr(unit, 'calls') else 0
                    }
                }
                for unit in units
            ]
        }
    
    def get_related_units(self, code_hash: str, threshold: float = 0.3, max_results: int = 10) -> List[Tuple[CodeRecord, float]]:
        """
        Get units related to a specific code unit.
        
        Args:
            code_hash: Hash of the code unit to find relations for
            threshold: Minimum similarity threshold
            max_results: Maximum number of results to return
            
        Returns:
            List of (record, similarity) tuples
        """
        record = self.records.get(code_hash)
        if not record or record.simhash is None:
            return []
        
        unit = self.code_units.get(code_hash)
        if not unit:
            return []
        
        # Find similar using BK-tree
        hamming_threshold = max(10, int(64 * (1.0 - threshold)))
        candidates = self.bk_tree.search(record.simhash, hamming_threshold)
        
        related = []
        for candidate_record, hamming_dist in candidates:
            if candidate_record.code_hash == code_hash:
                continue
            
            candidate_unit = self.code_units.get(candidate_record.code_hash)
            if not candidate_unit:
                continue
            
            # Calculate actual similarity
            similarity = self.analyzer.calculate_structural_similarity(unit, candidate_unit)
            
            if similarity >= threshold:
                related.append((candidate_record, similarity))
        
        # Sort by similarity and limit results
        related.sort(key=lambda x: x[1], reverse=True)
        return related[:max_results]