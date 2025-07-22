"""
AST-based SimHash duplicate detection.
Uses structural analysis instead of text-based comparison.

This is now a facade that delegates to specialized core modules.
"""

import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from .ast_analyzer import ASTAnalyzer, CodeUnit
from .models import CodeRecord, SimilarityResult
from .ast_database import ASTDatabaseManager
from .trivial_filter import TrivialPatternFilter, TrivialFilterConfig
from .code_filter_utility import CodeFilterUtility

# Import core modules
from .core import (
    SimHashCalculator,
    DuplicateDetector,
    SimilarityGraphBuilder,
    CodeAnalyzer
)

logger = logging.getLogger(__name__)


class ASTSimHashDetector:
    """
    AST-based SimHash detector for structural code similarity.
    
    This class now acts as a facade, delegating responsibilities to specialized core modules:
    - SimHashCalculator: Manages SimHash calculations and BKTree operations
    - DuplicateDetector: Handles duplicate detection logic
    - SimilarityGraphBuilder: Builds similarity graphs
    - CodeAnalyzer: Provides code analysis and statistics
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
        
        # Initialize database
        self.db_manager = ASTDatabaseManager(db_path)
        
        # Initialize filters
        self.trivial_filter = TrivialPatternFilter(TrivialFilterConfig(), include_tests=include_tests)
        self.code_filter = CodeFilterUtility(include_tests=include_tests, include_trivial=False)
        
        # Initialize core modules
        self.simhash_calculator = SimHashCalculator(hamming_threshold)
        self.duplicate_detector = DuplicateDetector(
            self.simhash_calculator, 
            self.analyzer,
            self.code_filter
        )
        self.graph_builder = SimilarityGraphBuilder(
            self.simhash_calculator,
            self.analyzer
        )
        self.code_analyzer = CodeAnalyzer(
            self.analyzer,
            self.simhash_calculator
        )
        
        # Load existing data
        self._load_existing_data()
        
        logger.info(f"Initialized AST SimHash detector with threshold {hamming_threshold}, "
                   f"loaded {len(self.records)} existing records")
    
    # Compatibility properties
    @property
    def bk_tree(self):
        """Compatibility property for BKTree access."""
        return self.simhash_calculator.bk_tree
        
    @property
    def code_units(self):
        """Compatibility property for code units access."""
        return self.simhash_calculator.code_units
        
    @property
    def records(self):
        """Compatibility property for records access."""
        return self.simhash_calculator.records
    
    def _load_existing_data(self):
        """Load existing code records from database."""
        try:
            records = self.db_manager.load_all_records()
            logger.info(f"Loading {len(records)} records from database")
            
            for record in records:
                # Reconstruct CodeUnit from record
                unit = CodeUnit(
                    name=record.function_name or "",
                    type="function" if not record.function_name or not record.function_name.startswith("class ") else "class",
                    start_line=record.line_number or 0,
                    end_line=(record.line_number or 0) + record.source_code.count('\n'),
                    source_code=record.source_code,
                    file_path=record.full_path,
                    hash=record.code_hash,
                    simhash=record.simhash
                )
                
                # Add to calculator
                self.simhash_calculator.code_units[record.code_hash] = unit
                self.simhash_calculator.records[record.code_hash] = record
                self.simhash_calculator.bk_tree.add(record.code_hash)
                
        except Exception as e:
            logger.warning(f"Failed to load existing data: {e}")
    
    def register_file(self, file_path: str, force: bool = False) -> List[CodeRecord]:
        """
        Register all code units from a file.
        
        Args:
            file_path: Path to the Python file
            force: Force re-registration even if file exists
            
        Returns:
            List of registered CodeRecord objects
        """
        logger.info(f"Registering file: {file_path}")
        
        # Check if file already registered
        if not force:
            existing = self.db_manager.get_records_by_file(file_path)
            if existing:
                logger.info(f"File already registered with {len(existing)} records")
                return existing
        
        # Read and parse file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return []
        
        # Extract code units
        units = self.analyzer.extract_code_units(source_code, file_path)
        
        if not units:
            logger.warning(f"No code units found in {file_path}")
            return []
        
        # Filter units
        filtered_units = []
        for unit in units:
            if not self.code_filter.should_exclude_unit(unit):
                filtered_units.append(unit)
        
        logger.info(f"Found {len(filtered_units)} meaningful units (filtered from {len(units)})")
        
        # Register each unit
        new_records = []
        for unit in filtered_units:
            record = self._register_unit(unit)
            if record:
                new_records.append(record)
        
        logger.info(f"Registered {len(new_records)} new records from {file_path}")
        return new_records
    
    def register_code(self, source_code: str, function_name: Optional[str] = None,
                     file_path: Optional[str] = None, line_number: Optional[int] = None) -> Optional[CodeRecord]:
        """
        Register a code snippet.
        
        Args:
            source_code: The source code to register
            function_name: Optional function/class name
            file_path: Optional file path
            line_number: Optional line number
            
        Returns:
            CodeRecord if registered successfully, None otherwise
        """
        units = self.analyzer.extract_code_units(source_code, file_path or "")
        
        if not units:
            logger.warning("No code units found in provided code")
            return None
        
        # Use the first unit
        unit = units[0]
        if function_name:
            unit.name = function_name
        if line_number is not None:
            unit.line_number = line_number
            unit.start_line = line_number
        
        return self._register_unit(unit)
    
    def _register_unit(self, unit: CodeUnit) -> Optional[CodeRecord]:
        """Register a single code unit."""
        # Check if already exists
        if unit.hash in self.simhash_calculator.code_units:
            logger.debug(f"Unit already registered: {unit.name}")
            return self.simhash_calculator.records.get(unit.hash)
        
        # Add to calculator
        record = self.simhash_calculator.add_code_unit(unit)
        if record:
            # Save to database
            try:
                self.db_manager.save_record(record)
            except Exception as e:
                logger.error(f"Failed to save record to database: {e}")
        
        return record
    
    def find_similar(self, source_code: str, function_name: Optional[str] = None,
                    file_path: Optional[str] = None, line_number: Optional[int] = None,
                    threshold: float = 0.7) -> SimilarityResult:
        """
        Find similar code to the given source code.
        
        Delegates to DuplicateDetector.
        """
        return self.duplicate_detector.find_similar(
            source_code, function_name, file_path, line_number, threshold
        )
    
    def analyze_code_structure(self, source_code: str, file_path: Optional[str] = None) -> Dict:
        """
        Analyze code structure without registering.
        
        Delegates to CodeAnalyzer.
        """
        return self.code_analyzer.analyze_code_structure(source_code, file_path)
    
    def get_statistics(self) -> Dict:
        """
        Get detector statistics.
        
        Delegates to CodeAnalyzer.
        """
        return self.code_analyzer.get_statistics()
    
    def clear_memory(self):
        """Clear all in-memory data."""
        self.simhash_calculator.clear()
        logger.info("Cleared all in-memory data")
    
    def get_all_records(self) -> List[CodeRecord]:
        """Get all stored records."""
        return self.simhash_calculator.get_all_records()
    
    def find_potential_duplicates(self, threshold: float = 0.8, use_fast_mode: bool = True, 
                                use_cache: bool = True, include_trivial: bool = False, 
                                silent: bool = False, top_percent: Optional[float] = None) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """
        Find potential duplicate pairs.
        
        Delegates to DuplicateDetector.
        """
        return self.duplicate_detector.find_potential_duplicates(
            threshold, use_fast_mode, use_cache, include_trivial, silent, top_percent
        )
    
    def build_similarity_graph(self, threshold: float = 0.3, use_fast_mode: bool = True) -> Dict[str, List[Tuple[str, float]]]:
        """
        Build a similarity graph.
        
        Delegates to SimilarityGraphBuilder.
        """
        return self.graph_builder.build_similarity_graph(threshold, use_fast_mode)
    
    def get_related_units(self, code_hash: str, threshold: float = 0.3, max_results: int = 10) -> List[Tuple[CodeRecord, float]]:
        """
        Get units related to a specific code unit.
        
        Delegates to SimilarityGraphBuilder.
        """
        return self.graph_builder.get_related_units(code_hash, threshold, max_results)
    
    def find_relations_adaptive(self, target_connections: int = 200, max_connections: int = 1000,
                              initial_threshold: float = 0.7) -> Dict[str, List[Tuple[str, float]]]:
        """
        Build similarity graph with adaptive threshold.
        
        Delegates to SimilarityGraphBuilder.
        """
        return self.graph_builder.find_relations_adaptive(
            target_connections, max_connections, initial_threshold
        )
    
    # Compatibility method for old code
    def _is_meaningful_for_refactoring(self, record: CodeRecord) -> bool:
        """
        Check if a code record is meaningful for refactoring.
        Kept for backward compatibility.
        """
        return not self.code_filter.should_exclude_record(record)