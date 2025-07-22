"""Structural duplicate detection using AST-based similarity analysis."""

import logging
from typing import Dict, List, Tuple, Any

from ..models import CodeRecord
from ..ast_simhash_detector import ASTSimHashDetector


class StructuralDuplicateDetector:
    """Detector for structural code duplicates using AST-based analysis."""
    
    def __init__(self):
        """Initialize structural duplicate detector."""
        self.detector = ASTSimHashDetector()
        self.logger = logging.getLogger(__name__)
        
    async def detect_duplicates(
        self, 
        code_records: List[CodeRecord],
        threshold: float = 0.7,
        use_fast_mode: bool = True
    ) -> Dict[str, Any]:
        """Detect structural duplicates in code records.
        
        Args:
            code_records: List of code records to analyze
            threshold: Similarity threshold for duplicate detection
            use_fast_mode: Whether to use fast detection mode
            
        Returns:
            Dictionary containing categorized duplicate results
        """
        try:
            # Register code records
            for record in code_records:
                if record.code_content and record.function_name:
                    self.detector.register_code(
                        record.code_content, 
                        record.function_name, 
                        record.file_path
                    )
            
            # Find potential duplicates
            duplicates = self.detector.find_potential_duplicates(
                threshold=threshold, 
                use_fast_mode=use_fast_mode, 
                silent=True
            )
            
            # Categorize by confidence
            categorized = self._categorize_duplicates(duplicates)
            
            return {
                **categorized,
                "total_found": len(duplicates)
            }
        except Exception as e:
            self.logger.error(f"Structural duplicate detection failed: {e}")
            return {
                "high_confidence": [],
                "medium_confidence": [],
                "low_confidence": [],
                "total_found": 0,
                "error": str(e)
            }
    
    def _categorize_duplicates(
        self, 
        duplicates: List[Tuple[CodeRecord, CodeRecord, float]]
    ) -> Dict[str, List[Tuple[CodeRecord, CodeRecord, float]]]:
        """Categorize duplicates by confidence level.
        
        Args:
            duplicates: List of duplicate tuples (record1, record2, similarity)
            
        Returns:
            Dictionary with categorized duplicates
        """
        high_confidence = []
        medium_confidence = []
        low_confidence = []
        
        for duplicate in duplicates:
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