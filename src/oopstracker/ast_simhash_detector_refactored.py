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
from .services.registration_service import RegistrationService
from .services.similarity_search_service import SimilaritySearchService
from .services.ast_code_analysis_service import ASTCodeAnalysisService

logger = logging.getLogger(__name__)


class ASTSimHashDetectorRefactored:
    """
    AST-based SimHash detector for structural code similarity.
    
    This refactored version acts as a facade that delegates responsibilities to:
    - RegistrationService: Code registration and file management
    - SimilaritySearchService: Similarity search operations
    - ASTCodeAnalysisService: Code structure analysis and statistics
    - Existing detectors: Duplicate detection and graph analysis
    
    This class maintains backward compatibility while improving separation of concerns.
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
        
        # Initialize service layers
        self.registration_service = RegistrationService(
            self.analyzer, self.db_manager, self.records, self.code_units, self.bk_tree
        )
        self.similarity_search_service = SimilaritySearchService(
            self.analyzer, self.records, self.code_units, self.bk_tree, self.hamming_threshold
        )
        self.code_analysis_service = ASTCodeAnalysisService(
            self.analyzer, self.records, self.code_units, self.hamming_threshold
        )
        
        # Initialize components for duplicate detection and graph analysis (kept for now)
        from .detectors import (SimilarityDetector, SimilarityGraphBuilder, DetectorCacheManager,
                               AdaptiveThresholdFinder, TopPercentDuplicateFinder)
        self.similarity_detector = SimilarityDetector(self.analyzer, self.code_filter)
        self.graph_builder = SimilarityGraphBuilder(self.analyzer)
        self.cache_manager = DetectorCacheManager()
        self.adaptive_threshold_finder = AdaptiveThresholdFinder(self.graph_builder)
        self.top_percent_finder = TopPercentDuplicateFinder(self.similarity_detector, self.hamming_threshold)
        
        # Load existing data
        self.registration_service.load_existing_data()
        
        logger.info(f"Initialized AST SimHash detector with threshold {hamming_threshold}, loaded {len(self.records)} existing records")
    
    
    def register_file(self, file_path: str, force: bool = False) -> List[CodeRecord]:
        """
        Register all functions and classes from a Python file.
        Delegates to RegistrationService.
        """
        return self.registration_service.register_file(file_path, force)
    
    def register_code(self, source_code: str, function_name: Optional[str] = None,
                      file_path: Optional[str] = None) -> Optional[CodeRecord]:
        """
        Register a single piece of code.
        Delegates to RegistrationService.
        """
        return self.registration_service.register_code(source_code, function_name, file_path)
    
    
    def find_similar(self, source_code: str, function_name: Optional[str] = None,
                     threshold: float = 0.7) -> SimilarityResult:
        """
        Find similar code to the given source.
        Delegates to SimilaritySearchService.
        """
        return self.similarity_search_service.find_similar(source_code, function_name, threshold)
    
    
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
        return self.code_analysis_service.get_statistics()
    
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
        Delegates to ASTCodeAnalysisService.
        """
        return self.code_analysis_service.get_all_records()
    
    def analyze_code_structure(self, source_code: str, file_path: Optional[str] = None) -> Dict:
        """
        Analyze the structure of given source code.
        Delegates to ASTCodeAnalysisService.
        """
        return self.code_analysis_service.analyze_code_structure(source_code, file_path)
    
    def get_related_units(self, code_hash: str, threshold: float = 0.3, max_results: int = 10) -> List[Tuple[CodeRecord, float]]:
        """
        Get units related to a specific code unit.
        Delegates to SimilaritySearchService.
        """
        return self.similarity_search_service.get_related_units(code_hash, threshold, max_results)