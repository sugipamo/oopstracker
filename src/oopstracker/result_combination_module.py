"""Result combination module for merging structural and semantic analysis results."""

import logging
from typing import Dict, List, Any, Tuple
from .models import CodeRecord
from .semantic_analysis_module import SemanticDuplicateResult, SemanticAnalysisStatus


class ResultCombinationModule:
    """Module for combining results from different analysis methods."""
    
    def __init__(self):
        """Initialize result combination module."""
        self.logger = logging.getLogger(__name__)
    
    def combine_results(
        self,
        structural_results: Dict[str, Any],
        semantic_results: List[SemanticDuplicateResult],
        code_records: List[CodeRecord]
    ) -> Dict[str, Any]:
        """Combine structural and semantic analysis results.
        
        Args:
            structural_results: Results from structural analysis
            semantic_results: Results from semantic analysis
            code_records: Original code records
            
        Returns:
            Combined analysis results
        """
        
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
                self._is_same_pair(structural_duplicate, s)
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
        
        # Calculate statistics
        total_structural = len(structural_results.get("high_confidence", []))
        total_semantic_analyzed = len(semantic_results)
        structural_only_count = total_structural - sum(
            1 for s in semantic_results 
            if any(self._is_same_pair(struct, s) 
                   for struct in structural_results.get("high_confidence", []))
        )
        
        return {
            "duplicate_groups": duplicate_groups,
            "total_groups": len(duplicate_groups),
            "semantic_analyzed": total_semantic_analyzed,
            "structural_only": max(0, structural_only_count),
            "summary": self._generate_summary(duplicate_groups, code_records),
            "statistics": {
                "total_records": len(code_records),
                "semantic_duplicates": sum(1 for g in duplicate_groups if g["type"] == "semantic"),
                "structural_duplicates": sum(1 for g in duplicate_groups if g["type"] == "structural_only"),
                "average_similarity": self._calculate_average_similarity(duplicate_groups)
            }
        }
    
    def _is_same_pair(
        self, 
        structural_duplicate: Tuple, 
        semantic_result: SemanticDuplicateResult
    ) -> bool:
        """Check if structural duplicate and semantic result refer to the same pair.
        
        Args:
            structural_duplicate: Tuple from structural analysis
            semantic_result: Result from semantic analysis
            
        Returns:
            True if they refer to the same code pair
        """
        if len(structural_duplicate) < 2:
            return False
            
        return (
            structural_duplicate[0] == semantic_result.code_record_1 and
            structural_duplicate[1] == semantic_result.code_record_2
        ) or (
            structural_duplicate[0] == semantic_result.code_record_2 and
            structural_duplicate[1] == semantic_result.code_record_1
        )
    
    def _generate_summary(
        self, 
        duplicate_groups: List[Dict[str, Any]], 
        code_records: List[CodeRecord]
    ) -> str:
        """Generate a summary of the analysis results.
        
        Args:
            duplicate_groups: Combined duplicate groups
            code_records: Original code records
            
        Returns:
            Summary text
        """
        if not duplicate_groups:
            return f"No duplicates found among {len(code_records)} code records."
        
        semantic_count = sum(1 for g in duplicate_groups if g["type"] == "semantic")
        structural_count = sum(1 for g in duplicate_groups if g["type"] == "structural_only")
        
        summary_parts = [
            f"Found {len(duplicate_groups)} duplicate groups among {len(code_records)} code records."
        ]
        
        if semantic_count > 0:
            summary_parts.append(f"{semantic_count} confirmed by semantic analysis.")
        
        if structural_count > 0:
            summary_parts.append(f"{structural_count} detected by structural analysis only.")
        
        return " ".join(summary_parts)
    
    def _calculate_average_similarity(self, duplicate_groups: List[Dict[str, Any]]) -> float:
        """Calculate average similarity across all duplicate groups.
        
        Args:
            duplicate_groups: List of duplicate groups
            
        Returns:
            Average similarity score
        """
        if not duplicate_groups:
            return 0.0
        
        total_similarity = sum(g.get("similarity", 0.0) for g in duplicate_groups)
        return total_similarity / len(duplicate_groups)