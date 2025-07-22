"""
Duplicate detection functionality.
"""

import logging
from typing import List, Tuple, Dict, Optional, Set

from ...models import CodeRecord, SimilarityResult
from ...ast_analyzer import ASTAnalyzer, CodeUnit
from ...progress_reporter import ProgressReporter
from ...code_filter_utility import CodeFilterUtility
from ..simhash import SimHashCalculator

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """
    Detects duplicate code using various strategies.
    """
    
    def __init__(self, simhash_calculator: SimHashCalculator, 
                 analyzer: ASTAnalyzer,
                 code_filter: CodeFilterUtility):
        """
        Initialize duplicate detector.
        
        Args:
            simhash_calculator: SimHash calculator instance
            analyzer: AST analyzer for structural similarity
            code_filter: Code filter for excluding trivial code
        """
        self.simhash_calculator = simhash_calculator
        self.analyzer = analyzer
        self.code_filter = code_filter
        self._duplicates_cache: Dict[str, List] = {}
        self._cache_timestamp = 0
        
    def find_similar(self, source_code: str, function_name: Optional[str] = None,
                    file_path: Optional[str] = None, line_number: Optional[int] = None,
                    threshold: float = 0.7) -> SimilarityResult:
        """
        Find similar code to the given source code.
        
        Args:
            source_code: Source code to find similarities for
            function_name: Optional function name
            file_path: Optional file path
            line_number: Optional line number
            threshold: Similarity threshold
            
        Returns:
            SimilarityResult containing similar code records
        """
        # Parse the target code
        units = self.analyzer.extract_code_units(source_code, file_path or "")
        
        if not units:
            logger.warning("No code units found in provided source code")
            return SimilarityResult(similar_records=[])
        
        # For now, just process the first unit
        target_unit = units[0]
        if function_name:
            target_unit.name = function_name
        if line_number is not None:
            target_unit.line_number = line_number
            
        # Find similar units
        similar_hashes = self.simhash_calculator.find_similar_hashes(target_unit.hash)
        similar_records = []
        
        for hash_value in similar_hashes:
            record = self.simhash_calculator.get_record(hash_value)
            unit = self.simhash_calculator.get_code_unit(hash_value)
            
            if record and unit:
                # Calculate actual similarity
                similarity = self.analyzer.calculate_structural_similarity(target_unit, unit)
                if similarity >= threshold:
                    similar_records.append((record, similarity))
                    
        # Sort by similarity descending
        similar_records.sort(key=lambda x: x[1], reverse=True)
        
        return SimilarityResult(
            similar_records=[rec for rec, _ in similar_records[:10]],  # Top 10
            similarity_scores=[score for _, score in similar_records[:10]]
        )
        
    def find_potential_duplicates(self, threshold: float = 0.8, 
                                use_fast_mode: bool = True,
                                use_cache: bool = True,
                                include_trivial: bool = False,
                                silent: bool = False,
                                top_percent: Optional[float] = None) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """
        Find potential duplicate pairs across all registered code.
        
        Args:
            threshold: Minimum similarity threshold
            use_fast_mode: Use SimHash for pre-filtering (much faster)
            use_cache: Use cached results if available
            include_trivial: Include trivial duplicates
            silent: If True, suppress progress messages
            top_percent: If provided, dynamically adjust threshold
            
        Returns:
            List of (record1, record2, similarity_score) tuples
        """
        # Handle dynamic threshold adjustment for top N%
        if top_percent is not None:
            return self._find_top_percent_duplicates(
                top_percent, use_fast_mode, include_trivial, silent
            )
        
        logger.info(f"Searching for potential duplicates with threshold {threshold}")
        
        # Check cache
        records = self.simhash_calculator.get_all_records()
        cache_key = f"{threshold}_{use_fast_mode}_{include_trivial}_{len(records)}"
        current_timestamp = max((r.timestamp for r in records), default=0)
        
        if use_cache and cache_key in self._duplicates_cache and current_timestamp <= self._cache_timestamp:
            logger.info("Using cached duplicate detection results")
            return self._duplicates_cache[cache_key]
        
        # Compute duplicates
        if use_fast_mode:
            duplicates = self._find_duplicates_fast(records, threshold, include_trivial, silent)
        else:
            duplicates = self._find_duplicates_exhaustive(records, threshold, include_trivial, silent)
        
        # Update cache
        if use_cache:
            self._duplicates_cache[cache_key] = duplicates
            self._cache_timestamp = current_timestamp
            logger.info(f"Cached {len(duplicates)} duplicate pairs")
        
        return duplicates
        
    def _find_duplicates_fast(self, records: List[CodeRecord], threshold: float,
                            include_trivial: bool = False, silent: bool = False) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """Fast duplicate detection using SimHash pre-filtering."""
        duplicates = []
        processed_pairs: Set[Tuple[str, str]] = set()
        
        # Calculate appropriate hamming threshold
        hamming_threshold = max(1, int(self.simhash_calculator.hamming_threshold * (1.0 - threshold)))
        logger.info(f"Using SimHash hamming threshold: {hamming_threshold}")
        
        # Filter records
        if include_trivial:
            meaningful_records = records
        else:
            meaningful_records = [r for r in records if not self.code_filter.should_exclude_record(r)]
        
        logger.info(f"Processing {len(meaningful_records)} records")
        
        # Create progress reporter
        progress_reporter = ProgressReporter(
            interval_seconds=5.0,
            min_items_for_display=100,
            silent=silent
        )
        
        for i, record1 in enumerate(meaningful_records):
            progress_reporter.print_progress(i + 1, len(meaningful_records), unit="records")
            
            unit1 = self.simhash_calculator.get_code_unit(record1.code_hash)
            if not unit1 or record1.simhash is None:
                continue
            
            # Find similar records by SimHash
            similar_hashes = self.simhash_calculator.find_similar_hashes(
                record1.code_hash, hamming_threshold
            )
            
            for hash_value in similar_hashes:
                # Skip self
                if hash_value == record1.code_hash:
                    continue
                    
                record2 = self.simhash_calculator.get_record(hash_value)
                if not record2:
                    continue
                
                # Avoid duplicate pairs
                pair_key = tuple(sorted([record1.code_hash, record2.code_hash]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)
                
                unit2 = self.simhash_calculator.get_code_unit(record2.code_hash)
                if not unit2:
                    continue
                
                # Skip if same location
                if (unit1.file_path == unit2.file_path and 
                    unit1.start_line == unit2.start_line):
                    continue
                
                # Calculate actual similarity
                similarity = self.analyzer.calculate_structural_similarity(unit1, unit2)
                
                if similarity >= threshold:
                    duplicates.append((record1, record2, similarity))
        
        # Sort by similarity descending
        duplicates.sort(key=lambda x: x[2], reverse=True)
        logger.info(f"Found {len(duplicates)} potential duplicates")
        return duplicates
        
    def _find_duplicates_exhaustive(self, records: List[CodeRecord], threshold: float,
                                  include_trivial: bool = False, silent: bool = False) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """Exhaustive O(n²) duplicate detection."""
        duplicates = []
        
        # Filter records
        if include_trivial:
            meaningful_records = records
        else:
            meaningful_records = [r for r in records if not self.code_filter.should_exclude_record(r)]
            
        logger.info(f"Exhaustive search on {len(meaningful_records)} records")
        
        for i, record1 in enumerate(meaningful_records):
            unit1 = self.simhash_calculator.get_code_unit(record1.code_hash)
            if not unit1:
                continue
            
            for j, record2 in enumerate(meaningful_records[i+1:], i+1):
                unit2 = self.simhash_calculator.get_code_unit(record2.code_hash)
                if not unit2:
                    continue
                
                # Skip if same location
                if (unit1.file_path == unit2.file_path and 
                    unit1.start_line == unit2.start_line):
                    continue
                
                # Calculate similarity
                similarity = self.analyzer.calculate_structural_similarity(unit1, unit2)
                
                if similarity >= threshold:
                    duplicates.append((record1, record2, similarity))
                    
        # Sort by similarity descending
        duplicates.sort(key=lambda x: x[2], reverse=True)
        logger.info(f"Found {len(duplicates)} potential duplicates")
        return duplicates
        
    def _find_top_percent_duplicates(self, top_percent: float, use_fast_mode: bool = True,
                                   include_trivial: bool = False, silent: bool = False) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """Find top N% of duplicates by dynamically adjusting threshold."""
        logger.info(f"Finding top {top_percent}% of duplicates")
        
        # Start with a low threshold to capture more pairs
        initial_threshold = 0.3
        all_duplicates = self.find_potential_duplicates(
            threshold=initial_threshold,
            use_fast_mode=use_fast_mode,
            use_cache=False,
            include_trivial=include_trivial,
            silent=silent
        )
        
        if not all_duplicates:
            return []
            
        # Calculate target count
        records = self.simhash_calculator.get_all_records()
        if include_trivial:
            total_pairs = len(records) * (len(records) - 1) // 2
        else:
            meaningful = [r for r in records if not self.code_filter.should_exclude_record(r)]
            total_pairs = len(meaningful) * (len(meaningful) - 1) // 2
            
        target_count = int(total_pairs * (top_percent / 100.0))
        
        # Return top N pairs
        return all_duplicates[:target_count]