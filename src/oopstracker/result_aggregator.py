"""Result aggregation and recommendation for duplicate detection."""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class DuplicateAnalysisResult:
    """Comprehensive duplicate analysis result."""
    structural_results: Dict[str, Any]
    semantic_results: List[Any]
    total_records: int
    summary: Dict[str, Any]
    recommendation: str


class ResultAggregator:
    """Aggregates and analyzes duplicate detection results."""
    
    def __init__(self):
        """Initialize result aggregator."""
        pass
    
    def aggregate_results(
        self,
        structural_results: Dict[str, Any],
        semantic_results: List[Any],
        total_records: int
    ) -> DuplicateAnalysisResult:
        """
        Aggregate structural and semantic analysis results.
        
        Args:
            structural_results: Results from structural duplicate detection
            semantic_results: Results from semantic duplicate detection
            total_records: Total number of records analyzed
            
        Returns:
            Comprehensive analysis result
        """
        summary = self._generate_summary(structural_results, semantic_results, total_records)
        recommendation = self._get_recommendation(structural_results, semantic_results)
        
        return DuplicateAnalysisResult(
            structural_results=structural_results,
            semantic_results=semantic_results,
            total_records=total_records,
            summary=summary,
            recommendation=recommendation
        )
    
    def _generate_summary(
        self,
        structural_results: Dict[str, Any],
        semantic_results: List[Any],
        total_records: int
    ) -> Dict[str, Any]:
        """Generate comprehensive summary of duplicate detection results."""
        structural_duplicates = structural_results.get("duplicate_groups", [])
        semantic_count = len(semantic_results)
        
        # Calculate structural statistics
        structural_duplicate_count = sum(len(group) - 1 for group in structural_duplicates)
        structural_rate = (structural_duplicate_count / total_records * 100) if total_records > 0 else 0
        
        # Analyze semantic results
        high_confidence_semantic = [r for r in semantic_results if getattr(r, 'confidence', 0) > 0.8]
        medium_confidence_semantic = [r for r in semantic_results if 0.5 < getattr(r, 'confidence', 0) <= 0.8]
        
        return {
            "total_records": total_records,
            "structural_analysis": {
                "duplicate_groups": len(structural_duplicates),
                "duplicate_records": structural_duplicate_count,
                "duplication_rate": f"{structural_rate:.1f}%"
            },
            "semantic_analysis": {
                "pairs_analyzed": semantic_count,
                "high_confidence_duplicates": len(high_confidence_semantic),
                "medium_confidence_duplicates": len(medium_confidence_semantic)
            },
            "overall_health": self._assess_overall_health(structural_rate, semantic_count)
        }
    
    def _get_recommendation(
        self,
        structural_results: Dict[str, Any],
        semantic_results: List[Any]
    ) -> str:
        """Generate actionable recommendations based on analysis results."""
        structural_duplicates = structural_results.get("duplicate_groups", [])
        high_confidence_semantic = [r for r in semantic_results if getattr(r, 'confidence', 0) > 0.8]
        
        recommendations = []
        
        # Structural recommendations
        if len(structural_duplicates) > 10:
            recommendations.append(
                f"Found {len(structural_duplicates)} groups of structural duplicates. "
                "Consider consolidating duplicate implementations."
            )
        
        # Semantic recommendations
        if high_confidence_semantic:
            recommendations.append(
                f"Detected {len(high_confidence_semantic)} semantically similar code pairs. "
                "Review these for potential refactoring opportunities."
            )
        
        # General recommendations
        if not recommendations:
            return "✅ Code duplication is within acceptable limits."
        
        return " ".join(recommendations)
    
    def _assess_overall_health(self, duplication_rate: float, semantic_pairs: int) -> str:
        """Assess overall code health based on duplication metrics."""
        if duplication_rate < 5 and semantic_pairs < 5:
            return "Excellent"
        elif duplication_rate < 10 and semantic_pairs < 10:
            return "Good"
        elif duplication_rate < 20 and semantic_pairs < 20:
            return "Fair"
        else:
            return "Needs Improvement"