"""Duplicate Analyzer - Extracted duplicate detection logic."""

import asyncio
import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from ..models import CodeRecord
from ..ast_simhash_detector import ASTSimHashDetector


class DuplicateAnalyzer:
    """Analyzes code duplicates using structural and semantic methods."""
    
    def __init__(self):
        """Initialize duplicate analyzer."""
        self.logger = logging.getLogger(__name__)
        self.structural_detector = ASTSimHashDetector()
        self._semantic_threshold = 0.7
    
    async def analyze_structural_duplicates(
        self, 
        code_records: List[CodeRecord],
        threshold: float = 0.7,
        use_fast_mode: bool = True
    ) -> Dict[str, Any]:
        """Detect duplicates using structural analysis.
        
        Args:
            code_records: List of code records to analyze
            threshold: Similarity threshold for duplicate detection
            use_fast_mode: Whether to use fast mode for detection
            
        Returns:
            Dictionary containing categorized duplicate results
        """
        # Register code records with structural detector
        for record in code_records:
            if record.code_content and record.function_name:
                self.structural_detector.register_code(
                    record.code_content, 
                    record.function_name, 
                    record.file_path
                )
        
        # Find potential duplicates
        duplicates = self.structural_detector.find_potential_duplicates(
            threshold=threshold, 
            use_fast_mode=use_fast_mode, 
            silent=True
        )
        
        # Categorize by confidence
        result = self._categorize_duplicates(duplicates)
        result["total_found"] = len(duplicates)
        
        return result
    
    def _categorize_duplicates(
        self, 
        duplicates: List[Tuple[CodeRecord, CodeRecord, float]]
    ) -> Dict[str, List]:
        """Categorize duplicates by confidence level.
        
        Args:
            duplicates: List of duplicate tuples
            
        Returns:
            Dictionary with high, medium, and low confidence lists
        """
        high_confidence = []
        medium_confidence = []
        low_confidence = []
        
        for duplicate in duplicates:
            # duplicate is a tuple (CodeRecord, CodeRecord, float)
            if len(duplicate) >= 3:
                similarity = duplicate[2]
                if similarity >= 0.9:
                    high_confidence.append(duplicate)
                elif similarity >= 0.7:
                    medium_confidence.append(duplicate)
                else:
                    low_confidence.append(duplicate)
            else:
                # Fallback categorization
                medium_confidence.append(duplicate)
        
        return {
            "high_confidence": high_confidence,
            "medium_confidence": medium_confidence,
            "low_confidence": low_confidence
        }
    
    def normalize_code_indentation(self, code: str) -> str:
        """Normalize code indentation for consistent comparison.
        
        Args:
            code: Code string to normalize
            
        Returns:
            Normalized code string
        """
        lines = code.split('\n')
        if not lines:
            return code
        
        # Find minimum indentation (excluding empty lines)
        min_indent = float('inf')
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                min_indent = min(min_indent, indent)
        
        if min_indent == float('inf'):
            return code
        
        # Remove minimum indentation from all lines
        normalized_lines = []
        for line in lines:
            if line.strip():
                normalized_lines.append(line[min_indent:])
            else:
                normalized_lines.append(line)
        
        return '\n'.join(normalized_lines)
    
    def prepare_code_pairs(
        self,
        structural_candidates: List[Tuple[CodeRecord, CodeRecord, float]],
        max_pairs: int = 20
    ) -> List[Tuple[str, str, Tuple[CodeRecord, CodeRecord, float]]]:
        """Prepare code pairs for semantic analysis.
        
        Args:
            structural_candidates: List of structural duplicate candidates
            max_pairs: Maximum number of pairs to prepare
            
        Returns:
            List of normalized code pairs with original candidate data
        """
        code_pairs = []
        
        for candidate in structural_candidates[:max_pairs]:
            if len(candidate) >= 2 and hasattr(candidate[0], 'code_content') and hasattr(candidate[1], 'code_content'):
                code1 = self.normalize_code_indentation(candidate[0].code_content)
                code2 = self.normalize_code_indentation(candidate[1].code_content)
                code_pairs.append((code1, code2, candidate))
        
        return code_pairs