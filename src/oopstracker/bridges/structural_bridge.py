"""Bridge for structural analysis functionality."""

from typing import Dict, List, Any, Tuple
import logging
from ..models import CodeRecord
from ..ast_simhash_detector import ASTSimHashDetector


class StructuralAnalysisBridge:
    """Bridge to structural analysis functionality."""
    
    def __init__(self):
        """Initialize structural analysis bridge."""
        self.detector = ASTSimHashDetector()
        self.logger = logging.getLogger(__name__)
        
    async def analyze(
        self, 
        code_records: List[CodeRecord],
        threshold: float = 0.7,
        use_fast_mode: bool = True
    ) -> Dict[str, Any]:
        """Perform structural duplicate detection.
        
        Args:
            code_records: List of code records to analyze
            threshold: Similarity threshold
            use_fast_mode: Whether to use fast mode
            
        Returns:
            Categorized structural duplicates
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
            
            # Find duplicates
            duplicates = self.detector.find_potential_duplicates(
                threshold=threshold, 
                use_fast_mode=use_fast_mode, 
                silent=True
            )
            
            # Categorize by confidence
            return self._categorize_duplicates(duplicates)
            
        except Exception as e:
            self.logger.error(f"Structural duplicate detection failed: {e}")
            return self._empty_results(str(e))
    
    def _categorize_duplicates(
        self, 
        duplicates: List[Tuple[CodeRecord, CodeRecord, float]]
    ) -> Dict[str, Any]:
        """Categorize duplicates by confidence level."""
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
                medium_confidence.append(duplicate)
        
        return {
            "high_confidence": high_confidence,
            "medium_confidence": medium_confidence,
            "low_confidence": low_confidence,
            "total_found": len(duplicates)
        }
    
    def _empty_results(self, error: str = None) -> Dict[str, Any]:
        """Return empty results structure."""
        result = {
            "high_confidence": [],
            "medium_confidence": [],
            "low_confidence": [],
            "total_found": 0
        }
        if error:
            result["error"] = error
        return result