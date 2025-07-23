"""
Similarity search service for finding similar code units.
Handles code similarity calculations and searches.
"""

import logging
from typing import List, Dict, Optional, Tuple

from ..ast_analyzer import ASTAnalyzer, CodeUnit
from ..models import CodeRecord, SimilarityResult
from ..simhash_detector import BKTree

logger = logging.getLogger(__name__)


class SimilaritySearchService:
    """Service for handling similarity search operations."""
    
    def __init__(self, analyzer: ASTAnalyzer, records: Dict[str, CodeRecord], 
                 code_units: Dict[str, CodeUnit], bk_tree: BKTree,
                 hamming_threshold: int = 10):
        """
        Initialize similarity search service.
        
        Args:
            analyzer: AST analyzer instance
            records: Shared records dictionary
            code_units: Shared code units dictionary
            bk_tree: BK-tree instance for SimHash operations
            hamming_threshold: Maximum Hamming distance for similarity
        """
        self.analyzer = analyzer
        self.records = records
        self.code_units = code_units
        self.bk_tree = bk_tree
        self.hamming_threshold = hamming_threshold
    
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
    
    def get_related_units(self, code_hash: str, threshold: float = 0.3, 
                         max_results: int = 10) -> List[Tuple[CodeRecord, float]]:
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