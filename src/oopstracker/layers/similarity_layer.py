"""
Similarity detection layer for AST SimHash detector.
Handles finding similar code and potential duplicates.
"""

import logging
from typing import List, Dict, Optional, Tuple

from ..models import CodeRecord, SimilarityResult
from ..ast_analyzer import ASTAnalyzer, CodeUnit
from ..detectors import SimilarityDetector, TopPercentDuplicateFinder
from ..code_filter_utility import CodeFilterUtility

logger = logging.getLogger(__name__)


class SimilarityDetectionLayer:
    """Handles similarity detection and duplicate finding."""
    
    def __init__(self, hamming_threshold: int = 10, include_tests: bool = False):
        """Initialize similarity detection layer."""
        self.hamming_threshold = hamming_threshold
        self.analyzer = ASTAnalyzer()
        self.code_filter = CodeFilterUtility(
            include_tests=include_tests, 
            include_trivial=False
        )
        self.similarity_detector = SimilarityDetector(
            self.analyzer, 
            self.code_filter
        )
        self.top_percent_finder = TopPercentDuplicateFinder(
            self.similarity_detector, 
            self.hamming_threshold
        )
        
    def find_similar(self, source_code: str, data_layer, 
                     function_name: Optional[str] = None,
                     threshold: float = 0.7) -> SimilarityResult:
        """
        Find similar code to the given source.
        
        Args:
            source_code: Python source code to compare
            data_layer: Data management layer instance
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
        
        return self._find_similar_unit(target_unit, data_layer)
    
    def _find_similar_unit(self, target_unit: CodeUnit, 
                           data_layer) -> SimilarityResult:
        """Find units similar to the given target unit."""
        # Calculate SimHash for target
        target_simhash = self.analyzer.calculate_simhash(target_unit)
        
        similar_units = []
        
        if target_simhash is not None:
            # Use BK-tree to find candidates
            candidates = data_layer.bk_tree.search(
                target_simhash, 
                self.hamming_threshold
            )
            
            for record, hamming_distance in candidates:
                unit = data_layer.get_unit(record.code_hash)
                if not unit:
                    continue
                
                # Calculate detailed similarity
                similarity = self.analyzer.calculate_structural_similarity(
                    target_unit, unit
                )
                
                similar_units.append({
                    'record': record,
                    'unit': unit,
                    'similarity': similarity,
                    'hamming_distance': hamming_distance
                })
        
        # Sort by similarity
        similar_units.sort(key=lambda x: x['similarity'], reverse=True)
        
        return SimilarityResult(similar_units=similar_units[:10])
    
    def find_potential_duplicates(self, data_layer, threshold: float = 0.8, 
                                  use_fast_mode: bool = True,
                                  include_trivial: bool = False, 
                                  silent: bool = False,
                                  top_percent: Optional[float] = None) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """
        Find potential duplicate pairs across all registered code.
        
        Args:
            data_layer: Data management layer instance
            threshold: Minimum similarity threshold
            use_fast_mode: Use SimHash for pre-filtering
            include_trivial: Include trivial duplicates
            silent: Suppress progress messages
            top_percent: If provided, find top N% of duplicates
            
        Returns:
            List of (record1, record2, similarity_score) tuples
        """
        # Handle dynamic threshold adjustment for top N%
        if top_percent is not None:
            return self._find_top_percent_duplicates(
                data_layer, top_percent, use_fast_mode, 
                include_trivial, silent
            )
        
        logger.info(f"Searching for duplicates with threshold {threshold}")
        
        records = data_layer.get_all_records()
        
        if use_fast_mode:
            duplicates = self.similarity_detector.find_duplicates_fast(
                records, data_layer.code_units, data_layer.bk_tree, 
                threshold, self.hamming_threshold, include_trivial, silent
            )
        else:
            duplicates = self.similarity_detector.find_duplicates_exhaustive(
                records, data_layer.code_units, threshold, 
                include_trivial, silent
            )
        
        return duplicates
    
    def _find_top_percent_duplicates(self, data_layer, top_percent: float, 
                                     use_fast_mode: bool = True,
                                     include_trivial: bool = False, 
                                     silent: bool = False) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """Find duplicates by dynamically adjusting threshold."""
        records = data_layer.get_all_records()
        return self.top_percent_finder.find_top_percent(
            records, data_layer.code_units, data_layer.bk_tree,
            top_percent, use_fast_mode, include_trivial, silent
        )
    
    def get_related_units(self, code_hash: str, data_layer,
                          threshold: float = 0.3, 
                          max_results: int = 10) -> List[Tuple[CodeRecord, float]]:
        """
        Get units related to a specific code unit.
        
        Args:
            code_hash: Hash of the code unit
            data_layer: Data management layer instance
            threshold: Minimum similarity threshold
            max_results: Maximum number of results
            
        Returns:
            List of (record, similarity) tuples
        """
        record = data_layer.get_record(code_hash)
        if not record or record.simhash is None:
            return []
        
        unit = data_layer.get_unit(code_hash)
        if not unit:
            return []
        
        # Find similar using BK-tree
        hamming_threshold = max(10, int(64 * (1.0 - threshold)))
        candidates = data_layer.bk_tree.search(record.simhash, hamming_threshold)
        
        related = []
        for candidate_record, hamming_dist in candidates:
            if candidate_record.code_hash == code_hash:
                continue
            
            candidate_unit = data_layer.get_unit(candidate_record.code_hash)
            if not candidate_unit:
                continue
            
            # Calculate actual similarity
            similarity = self.analyzer.calculate_structural_similarity(
                unit, candidate_unit
            )
            
            if similarity >= threshold:
                related.append((candidate_record, similarity))
        
        # Sort by similarity and limit results
        related.sort(key=lambda x: x[1], reverse=True)
        return related[:max_results]