"""Structural analysis component for duplicate detection."""

import logging
from typing import Dict, List, Tuple, Any
from ..models import CodeRecord
from ..ast_simhash_detector import ASTSimHashDetector


class StructuralAnalyzer:
    """Handle structural duplicate detection using AST SimHash."""
    
    def __init__(self):
        """Initialize structural analyzer."""
        self.logger = logging.getLogger(__name__)
        self.detector = ASTSimHashDetector()
    
    async def detect_duplicates(
        self, 
        code_records: List[CodeRecord]
    ) -> Dict[str, Any]:
        """Detect duplicates using structural analysis."""
        try:
            # Register code records with structural detector
            for record in code_records:
                if record.code_content and record.function_name:
                    self.detector.register_code(
                        record.code_content, 
                        record.function_name, 
                        record.file_path
                    )
            
            # Find potential duplicates (silent mode to avoid duplicate progress messages)
            duplicates = self.detector.find_potential_duplicates(
                threshold=0.7, use_fast_mode=True, silent=True
            )
            
            # Categorize by confidence  
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
                "low_confidence": low_confidence,
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