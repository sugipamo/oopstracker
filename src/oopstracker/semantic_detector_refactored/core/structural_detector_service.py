"""Structural duplicate detection service."""

import logging
from typing import Dict, List, Tuple, Any

from ...models import CodeRecord
from ...ast_simhash_detector import ASTSimHashDetector


class StructuralDetectorService:
    """Service for detecting structural duplicates in code."""
    
    def __init__(self):
        """Initialize structural detector service."""
        self.detector = ASTSimHashDetector()
        self.logger = logging.getLogger(__name__)
        self._default_threshold = 0.7
    
    async def detect_duplicates(
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
            Dictionary containing categorized duplicates by confidence level
        """
        try:
            # Register code records with structural detector
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
            
            return categorized
            
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
    ) -> Dict[str, Any]:
        """Categorize duplicates by confidence level.
        
        Args:
            duplicates: List of duplicate tuples with similarity scores
            
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
            "low_confidence": low_confidence,
            "total_found": len(duplicates)
        }
    
    def clear_cache(self) -> None:
        """Clear the detector's internal cache."""
        # Create a new detector instance to clear state
        self.detector = ASTSimHashDetector()