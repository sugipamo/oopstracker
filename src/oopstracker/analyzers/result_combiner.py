"""Result combination logic for duplicate detection."""

import logging
from typing import Dict, List, Any
from ..models import CodeRecord
from .semantic_analyzer import SemanticDuplicateResult, SemanticAnalysisStatus


class ResultCombiner:
    """Combine structural and semantic analysis results."""
    
    def __init__(self):
        """Initialize result combiner."""
        self.logger = logging.getLogger(__name__)
    
    def combine_results(
        self,
        structural_results: Dict[str, Any],
        semantic_results: List[SemanticDuplicateResult],
        code_records: List[CodeRecord]
    ) -> Dict[str, Any]:
        """Combine structural and semantic results."""
        
        # Create comprehensive duplicate groups
        duplicate_groups = []
        
        # Add high-confidence semantic duplicates
        for semantic_result in semantic_results:
            if semantic_result.status == SemanticAnalysisStatus.SUCCESS:
                duplicate_groups.append({
                    "type": "semantic",
                    "records": [semantic_result.code_record_1, semantic_result.code_record_2],
                    "similarity": semantic_result.semantic_similarity,
                    "confidence": semantic_result.confidence,
                    "method": semantic_result.analysis_method,
                    "reasoning": semantic_result.reasoning,
                    "analysis_time": semantic_result.analysis_time
                })
        
        # Add structural duplicates that weren't analyzed semantically
        for structural_duplicate in structural_results.get("high_confidence", []):
            # Check if this pair was already analyzed semantically
            # structural_duplicate is a tuple (CodeRecord, CodeRecord, float)
            already_analyzed = any(
                s.code_record_1 == structural_duplicate[0] and
                s.code_record_2 == structural_duplicate[1]
                for s in semantic_results
            )
            
            if not already_analyzed:
                duplicate_groups.append({
                    "type": "structural_only",
                    "records": [structural_duplicate[0], structural_duplicate[1]],
                    "similarity": structural_duplicate[2] if len(structural_duplicate) > 2 else 0.8,
                    "confidence": 0.7,  # Moderate confidence for structural only
                    "method": "structural_analysis",
                    "reasoning": "Structural similarity detected, semantic analysis not performed",
                    "analysis_time": 0.0
                })
        
        return {
            "duplicate_groups": duplicate_groups,
            "total_groups": len(duplicate_groups),
            "semantic_analyzed": len(semantic_results),
            "structural_only": len(structural_results.get("high_confidence", [])) - len(semantic_results)
        }