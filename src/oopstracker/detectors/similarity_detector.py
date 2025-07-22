"""
Similarity detection logic for AST SimHash detector.

This module contains the core similarity detection algorithms
extracted from the main AST SimHash detector.
"""

import logging
from typing import List, Tuple, Optional, Set
from ..models import CodeRecord
from ..ast_analyzer import ASTAnalyzer, CodeUnit
from ..simhash_detector import BKTree
from ..progress_reporter import ProgressReporter
from ..code_filter_utility import CodeFilterUtility

logger = logging.getLogger(__name__)


class SimilarityDetector:
    """Handles similarity detection between code records."""
    
    def __init__(self, analyzer: ASTAnalyzer, code_filter: CodeFilterUtility):
        """
        Initialize similarity detector.
        
        Args:
            analyzer: AST analyzer instance
            code_filter: Code filter utility instance
        """
        self.analyzer = analyzer
        self.code_filter = code_filter
    
    def find_duplicates_fast(
        self,
        records: List[CodeRecord],
        code_units: dict,
        bk_tree: BKTree,
        threshold: float,
        hamming_threshold: int,
        include_trivial: bool = False,
        silent: bool = False
    ) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """
        Fast duplicate detection using SimHash pre-filtering.
        
        Args:
            records: List of code records to check
            code_units: Mapping of hash to CodeUnit
            bk_tree: BK-tree for SimHash search
            threshold: Minimum similarity threshold
            hamming_threshold: Base hamming threshold for SimHash
            include_trivial: Include trivial duplicates
            silent: Suppress progress messages
            
        Returns:
            List of (record1, record2, similarity) tuples
        """
        duplicates = []
        processed_pairs = set()
        
        # Calculate appropriate hamming threshold for SimHash pre-filtering
        adjusted_hamming = max(1, int(hamming_threshold * (1.0 - threshold)))
        
        logger.info(f"Using SimHash hamming threshold: {adjusted_hamming}")
        
        # Filter records for meaningful duplicates if requested
        if include_trivial:
            meaningful_records = records
            logger.info(f"Including all {len(records)} records (trivial duplicates enabled)")
        else:
            meaningful_records = []
            for record in records:
                if not self.code_filter.should_exclude_record(record):
                    meaningful_records.append(record)
            logger.info(f"Filtered to {len(meaningful_records)} meaningful records from {len(records)} total")
        
        total_records = len(meaningful_records)
        
        # Create progress reporter
        progress_reporter = ProgressReporter(
            interval_seconds=5.0,
            min_items_for_display=100,
            silent=silent
        )
        
        for i, record1 in enumerate(meaningful_records):
            # Show progress for large datasets
            progress_reporter.print_progress(i + 1, total_records, unit="records")
            
            unit1 = code_units.get(record1.code_hash)
            if not unit1 or record1.simhash is None:
                continue
            
            # Use BK-tree to find similar records by SimHash
            similar_tuples = bk_tree.search(record1.simhash, adjusted_hamming)
            similar_records = [record for record, distance in similar_tuples]
            
            for record2 in similar_records:
                # Skip self
                if record1.code_hash == record2.code_hash:
                    continue
                
                # Avoid duplicate pairs
                pair_key = tuple(sorted([record1.code_hash, record2.code_hash]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)
                
                unit2 = code_units.get(record2.code_hash)
                if not unit2:
                    continue
                
                # Skip if same file and same function
                if (unit1.file_path == unit2.file_path and 
                    unit1.start_line == unit2.start_line):
                    continue
                
                # Calculate actual structural similarity
                similarity = self.analyzer.calculate_structural_similarity(unit1, unit2)
                
                if similarity >= threshold:
                    duplicates.append((record1, record2, similarity))
        
        # Sort by similarity descending
        duplicates.sort(key=lambda x: x[2], reverse=True)
        logger.info(f"Found {len(duplicates)} potential duplicates with fast mode")
        return duplicates
    
    def find_duplicates_exhaustive(
        self,
        records: List[CodeRecord],
        code_units: dict,
        threshold: float,
        include_trivial: bool = False,
        silent: bool = False
    ) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """
        Exhaustive O(n²) duplicate detection for maximum accuracy.
        
        Args:
            records: List of code records to check
            code_units: Mapping of hash to CodeUnit
            threshold: Minimum similarity threshold
            include_trivial: Include trivial duplicates
            silent: Suppress progress messages
            
        Returns:
            List of (record1, record2, similarity) tuples
        """
        duplicates = []
        
        # Filter records for meaningful duplicates if requested
        if include_trivial:
            meaningful_records = records
            logger.info(f"Including all {len(records)} records (trivial duplicates enabled)")
        else:
            meaningful_records = []
            for record in records:
                if not self.code_filter.should_exclude_record(record):
                    meaningful_records.append(record)
            logger.info(f"Filtered to {len(meaningful_records)} meaningful records from {len(records)} total")
        
        for i, record1 in enumerate(meaningful_records):
            unit1 = code_units.get(record1.code_hash)
            if not unit1:
                continue
            
            for j, record2 in enumerate(meaningful_records[i+1:], i+1):
                unit2 = code_units.get(record2.code_hash)
                if not unit2:
                    continue
                
                # Skip if same file and same function
                if (unit1.file_path == unit2.file_path and 
                    unit1.start_line == unit2.start_line):
                    continue
                
                similarity = self.analyzer.calculate_structural_similarity(unit1, unit2)
                
                if similarity >= threshold:
                    duplicates.append((record1, record2, similarity))
        
        # Sort by similarity descending
        duplicates.sort(key=lambda x: x[2], reverse=True)
        logger.info(f"Found {len(duplicates)} potential duplicates with exhaustive mode")
        return duplicates