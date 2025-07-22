"""
Top percent duplicate finder for similarity detection.

This module handles finding top N% most similar code pairs.
"""

import logging
from typing import List, Tuple, Dict, Optional

from ..models import CodeRecord
from ..ast_analyzer import CodeUnit
from .similarity_detector import SimilarityDetector

logger = logging.getLogger(__name__)


class TopPercentDuplicateFinder:
    """Find top N% most similar code pairs."""
    
    def __init__(
        self, 
        similarity_detector: SimilarityDetector,
        hamming_threshold: int
    ):
        """
        Initialize top percent duplicate finder.
        
        Args:
            similarity_detector: Detector for finding similar code
            hamming_threshold: Hamming distance threshold
        """
        self.similarity_detector = similarity_detector
        self.hamming_threshold = hamming_threshold
    
    def find_top_percent(
        self,
        records: List[CodeRecord],
        code_units: Dict[str, CodeUnit],
        bk_tree,
        top_percent: float,
        use_fast_mode: bool = True,
        include_trivial: bool = False,
        silent: bool = False
    ) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """
        Find duplicates by dynamically adjusting threshold to capture top N% most similar pairs.
        
        Args:
            records: List of code records
            code_units: Mapping of hash to CodeUnit
            bk_tree: BK-tree for fast similarity search
            top_percent: Percentage of top duplicates to find (0.0 to 100.0)
            use_fast_mode: Use SimHash for pre-filtering
            include_trivial: Include trivial duplicates
            silent: Suppress progress messages
            
        Returns:
            List of (record1, record2, similarity_score) tuples
        """
        if not 0.0 < top_percent <= 100.0:
            raise ValueError("top_percent must be between 0.0 and 100.0")
        
        # Calculate target number of pairs
        n_records = len(records)
        max_pairs = n_records * (n_records - 1) // 2
        target_pairs = int(max_pairs * (top_percent / 100.0))
        
        logger.info(f"Finding top {top_percent}% duplicates (targeting {target_pairs} pairs from {max_pairs} possible)")
        
        # Start with a high threshold and gradually lower it
        threshold = 0.95
        min_threshold = 0.3
        step = 0.05
        
        best_duplicates = []
        
        while threshold >= min_threshold:
            # Find duplicates at current threshold
            if use_fast_mode:
                duplicates = self.similarity_detector.find_duplicates_fast(
                    records, code_units, bk_tree, threshold,
                    self.hamming_threshold, include_trivial, silent
                )
            else:
                duplicates = self.similarity_detector.find_duplicates_exhaustive(
                    records, code_units, threshold, include_trivial, silent
                )
            
            logger.info(f"Threshold {threshold:.2f}: found {len(duplicates)} duplicates")
            
            if len(duplicates) >= target_pairs:
                # Found enough, trim to exact number
                duplicates.sort(key=lambda x: x[2], reverse=True)
                best_duplicates = duplicates[:target_pairs]
                break
            
            best_duplicates = duplicates
            threshold -= step
        
        logger.info(f"Returning {len(best_duplicates)} duplicates (target was {target_pairs})")
        return best_duplicates
    
    def find_top_n_duplicates(
        self,
        records: List[CodeRecord],
        code_units: Dict[str, CodeUnit],
        bk_tree,
        top_n: int,
        use_fast_mode: bool = True,
        include_trivial: bool = False,
        silent: bool = False
    ) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """
        Find top N most similar code pairs.
        
        Args:
            records: List of code records
            code_units: Mapping of hash to CodeUnit
            bk_tree: BK-tree for fast similarity search
            top_n: Number of top duplicates to find
            use_fast_mode: Use SimHash for pre-filtering
            include_trivial: Include trivial duplicates
            silent: Suppress progress messages
            
        Returns:
            List of (record1, record2, similarity_score) tuples
        """
        # Convert to percentage
        n_records = len(records)
        max_pairs = n_records * (n_records - 1) // 2
        
        if top_n > max_pairs:
            logger.warning(f"Requested {top_n} pairs but only {max_pairs} possible pairs exist")
            top_n = max_pairs
        
        top_percent = (top_n / max_pairs) * 100.0 if max_pairs > 0 else 100.0
        
        return self.find_top_percent(
            records, code_units, bk_tree, top_percent,
            use_fast_mode, include_trivial, silent
        )