"""Service for aggregating and reporting duplicate detection results with quality management."""

import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict

from ..models import CodeRecord
from .duplicate_analysis_strategy import (
    DuplicateAnalysisResult, 
    AnalysisConfidenceLevel,
    AnalysisMethod,
    ConfidenceCalculator
)


class DuplicateResultAggregator:
    """Aggregates and reports duplicate detection results with quality awareness."""
    
    def __init__(self):
        """Initialize result aggregator."""
        self.logger = logging.getLogger(__name__)
        self.confidence_calculator = ConfidenceCalculator()
    
    def aggregate_results(
        self,
        analysis_results: List[DuplicateAnalysisResult],
        code_records: List[CodeRecord],
        available_methods: List[AnalysisMethod]
    ) -> Dict[str, Any]:
        """Aggregate results from all detection methods with quality management.
        
        Args:
            analysis_results: All analysis results from various strategies
            code_records: Original code records analyzed
            available_methods: List of analysis methods that were available
            
        Returns:
            Comprehensive analysis results with quality indicators
        """
        # Group results by confidence level
        grouped_results = self._group_by_confidence(analysis_results)
        
        # Calculate quality metrics
        quality_metrics = self._calculate_quality_metrics(
            analysis_results, available_methods
        )
        
        # Generate recommendations based on quality
        recommendations = self._generate_quality_aware_recommendations(
            grouped_results, quality_metrics
        )
        
        # Create detailed summary
        summary = self._generate_detailed_summary(
            analysis_results, code_records, quality_metrics
        )
        
        return {
            "results_by_confidence": grouped_results,
            "quality_metrics": quality_metrics,
            "recommendations": recommendations,
            "summary": summary,
            "analysis_methods_used": list(set(r.analysis_method for r in analysis_results)),
            "total_duplicates_found": len(analysis_results)
        }
    
    def _group_by_confidence(
        self, 
        results: List[DuplicateAnalysisResult]
    ) -> Dict[str, List[DuplicateAnalysisResult]]:
        """Group results by confidence level.
        
        Args:
            results: Analysis results to group
            
        Returns:
            Dictionary grouped by confidence level
        """
        grouped = defaultdict(list)
        
        for result in results:
            grouped[result.confidence_level.value].append(result)
        
        # Ensure all confidence levels are present
        for level in AnalysisConfidenceLevel:
            if level.value not in grouped:
                grouped[level.value] = []
        
        return dict(grouped)
    
    def _calculate_quality_metrics(
        self,
        results: List[DuplicateAnalysisResult],
        available_methods: List[AnalysisMethod]
    ) -> Dict[str, Any]:
        """Calculate quality metrics for the analysis.
        
        Args:
            results: Analysis results
            available_methods: Methods that were available
            
        Returns:
            Quality metrics dictionary
        """
        total_results = len(results)
        
        # Count by method
        method_counts = defaultdict(int)
        for result in results:
            method_counts[result.analysis_method.value] += 1
        
        # Count by confidence
        confidence_counts = defaultdict(int)
        for result in results:
            confidence_counts[result.confidence_level.value] += 1
        
        # Calculate quality score (0-100)
        quality_score = self._calculate_overall_quality_score(
            results, available_methods
        )
        
        # Identify limitations
        limitations = self._identify_limitations(results, available_methods)
        
        return {
            "overall_quality_score": quality_score,
            "method_distribution": dict(method_counts),
            "confidence_distribution": dict(confidence_counts),
            "available_methods": [m.value for m in available_methods],
            "limitations": limitations,
            "has_semantic_analysis": AnalysisMethod.SEMANTIC_LLM in available_methods,
            "high_confidence_ratio": (
                confidence_counts[AnalysisConfidenceLevel.HIGH.value] / total_results
                if total_results > 0 else 0
            )
        }
    
    def _calculate_overall_quality_score(
        self,
        results: List[DuplicateAnalysisResult],
        available_methods: List[AnalysisMethod]
    ) -> float:
        """Calculate overall quality score (0-100).
        
        Args:
            results: Analysis results
            available_methods: Available analysis methods
            
        Returns:
            Quality score between 0 and 100
        """
        if not results:
            return 0.0
        
        # Base score on available methods
        method_score = 0
        if AnalysisMethod.SEMANTIC_LLM in available_methods:
            method_score = 40
        elif AnalysisMethod.HYBRID in available_methods:
            method_score = 30
        elif AnalysisMethod.STRUCTURAL_AST in available_methods:
            method_score = 20
        else:
            method_score = 10
        
        # Score based on confidence distribution
        confidence_weights = {
            AnalysisConfidenceLevel.HIGH: 1.0,
            AnalysisConfidenceLevel.MEDIUM: 0.7,
            AnalysisConfidenceLevel.LOW: 0.4,
            AnalysisConfidenceLevel.UNCERTAIN: 0.1
        }
        
        confidence_score = 0
        for result in results:
            confidence_score += confidence_weights.get(result.confidence_level, 0)
        
        if results:
            confidence_score = (confidence_score / len(results)) * 60
        
        return min(100, method_score + confidence_score)
    
    def _identify_limitations(
        self,
        results: List[DuplicateAnalysisResult],
        available_methods: List[AnalysisMethod]
    ) -> List[str]:
        """Identify analysis limitations.
        
        Args:
            results: Analysis results
            available_methods: Available methods
            
        Returns:
            List of limitation descriptions
        """
        limitations = []
        
        # Check method limitations
        if AnalysisMethod.SEMANTIC_LLM not in available_methods:
            limitations.append(
                "Semantic analysis unavailable - results based on structural patterns only"
            )
        
        # Check confidence limitations
        uncertain_count = sum(
            1 for r in results 
            if r.confidence_level == AnalysisConfidenceLevel.UNCERTAIN
        )
        if uncertain_count > len(results) * 0.3:
            limitations.append(
                f"High uncertainty: {uncertain_count} results have uncertain confidence"
            )
        
        # Collect unique limitations from results
        result_limitations = set()
        for result in results:
            result_limitations.update(result.limitations)
        
        limitations.extend(sorted(result_limitations))
        
        return limitations
    
    def _generate_quality_aware_recommendations(
        self,
        grouped_results: Dict[str, List[DuplicateAnalysisResult]],
        quality_metrics: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate recommendations based on quality analysis.
        
        Args:
            grouped_results: Results grouped by confidence
            quality_metrics: Calculated quality metrics
            
        Returns:
            List of recommendations with priority
        """
        recommendations = []
        
        # High-confidence duplicates
        high_conf_count = len(grouped_results.get(AnalysisConfidenceLevel.HIGH.value, []))
        if high_conf_count > 0:
            recommendations.append({
                "priority": "high",
                "action": f"Review and refactor {high_conf_count} high-confidence duplicates",
                "reason": "These duplicates are confirmed with high reliability"
            })
        
        # Quality concerns
        if quality_metrics["overall_quality_score"] < 50:
            recommendations.append({
                "priority": "medium",
                "action": "Consider enabling semantic analysis for better results",
                "reason": "Current analysis quality is limited without semantic understanding"
            })
        
        # Uncertain results
        uncertain_count = len(grouped_results.get(AnalysisConfidenceLevel.UNCERTAIN.value, []))
        if uncertain_count > 0:
            recommendations.append({
                "priority": "low",
                "action": f"Manually verify {uncertain_count} uncertain results",
                "reason": "These results need human validation due to analysis limitations"
            })
        
        return recommendations
    
    def _generate_detailed_summary(
        self,
        results: List[DuplicateAnalysisResult],
        code_records: List[CodeRecord],
        quality_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate detailed summary of analysis.
        
        Args:
            results: All analysis results
            code_records: Original code records
            quality_metrics: Quality metrics
            
        Returns:
            Detailed summary
        """
        return {
            "total_code_records_analyzed": len(code_records),
            "total_duplicates_found": len(results),
            "analysis_quality": {
                "score": quality_metrics["overall_quality_score"],
                "rating": self._get_quality_rating(quality_metrics["overall_quality_score"]),
                "has_semantic": quality_metrics["has_semantic_analysis"]
            },
            "duplicate_breakdown": {
                "high_confidence": len([r for r in results if r.confidence_level == AnalysisConfidenceLevel.HIGH]),
                "medium_confidence": len([r for r in results if r.confidence_level == AnalysisConfidenceLevel.MEDIUM]),
                "low_confidence": len([r for r in results if r.confidence_level == AnalysisConfidenceLevel.LOW]),
                "uncertain": len([r for r in results if r.confidence_level == AnalysisConfidenceLevel.UNCERTAIN])
            },
            "method_usage": quality_metrics["method_distribution"],
            "limitations": quality_metrics["limitations"]
        }
    
    def _get_quality_rating(self, score: float) -> str:
        """Get quality rating based on score.
        
        Args:
            score: Quality score (0-100)
            
        Returns:
            Quality rating string
        """
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "fair"
        elif score >= 20:
            return "limited"
        else:
            return "poor"