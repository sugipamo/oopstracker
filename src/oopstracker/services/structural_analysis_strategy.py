"""Structural analysis strategy for duplicate detection."""

import logging
from typing import List, Dict, Any

from .duplicate_analysis_strategy import (
    DuplicateAnalysisStrategy,
    DuplicateAnalysisResult,
    AnalysisMethod,
    AnalysisConfidenceLevel,
    ConfidenceCalculator,
    AnalysisContext
)
from ..models import CodeRecord
from ..detectors.structural_duplicate_detector import StructuralDuplicateDetector


class StructuralAnalysisStrategy(DuplicateAnalysisStrategy):
    """Strategy for structural code analysis using AST-based similarity."""
    
    def __init__(self):
        """Initialize structural analysis strategy."""
        self.detector = StructuralDuplicateDetector()
        self.logger = logging.getLogger(__name__)
        self.confidence_calculator = ConfidenceCalculator()
    
    async def analyze(
        self,
        code_records: List[CodeRecord],
        threshold: float = 0.7
    ) -> List[DuplicateAnalysisResult]:
        """Analyze code records for duplicates using structural analysis.
        
        Args:
            code_records: List of code records to analyze
            threshold: Similarity threshold
            
        Returns:
            List of duplicate analysis results
        """
        # Perform structural detection
        structural_results = await self.detector.detect_duplicates(
            code_records, threshold=threshold
        )
        
        # Convert to unified result format
        analysis_results = []
        
        # Process all confidence levels
        for confidence_key in ["high_confidence", "medium_confidence", "low_confidence"]:
            duplicates = structural_results.get(confidence_key, [])
            
            for duplicate in duplicates:
                if len(duplicate) >= 3:
                    result = self._create_analysis_result(
                        duplicate[0], duplicate[1], duplicate[2]
                    )
                    analysis_results.append(result)
        
        return analysis_results
    
    def get_method(self) -> AnalysisMethod:
        """Get the analysis method used by this strategy."""
        return AnalysisMethod.STRUCTURAL_AST
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get capabilities and limitations of this strategy."""
        return {
            "strengths": [
                "Fast performance",
                "No external dependencies",
                "Deterministic results",
                "Good for syntactic similarity"
            ],
            "limitations": [
                "Cannot detect semantic equivalence",
                "May miss refactored duplicates",
                "Limited to structural patterns"
            ],
            "best_for": [
                "Copy-paste detection",
                "Structural clones",
                "Quick initial analysis"
            ]
        }
    
    async def is_available(self) -> bool:
        """Check if this strategy is available for use."""
        # Structural analysis is always available
        return True
    
    def is_applicable(self, context: AnalysisContext) -> bool:
        """Check if this strategy is applicable for the given context.
        
        Args:
            context: Analysis context with requirements
            
        Returns:
            True if strategy can handle the context requirements
        """
        # Structural analysis is not suitable if semantic analysis is required
        if context.requires_semantic:
            return False
        
        # Good for fast processing requirements
        if context.max_processing_time and context.max_processing_time < 10.0:
            return True
        
        # Always applicable as a fallback
        return True
    
    def _create_analysis_result(
        self,
        record1: CodeRecord,
        record2: CodeRecord,
        similarity: float
    ) -> DuplicateAnalysisResult:
        """Create a unified analysis result.
        
        Args:
            record1: First code record
            record2: Second code record
            similarity: Similarity score
            
        Returns:
            Unified analysis result
        """
        # Calculate confidence based on similarity and method
        confidence = self.confidence_calculator.calculate_confidence(
            similarity_score=similarity,
            analysis_method=self.get_method(),
            additional_signals={"detection_method": "ast_simhash"}
        )
        
        # Generate reasoning
        if similarity >= 0.9:
            reasoning = "Very high structural similarity - likely copy-paste duplicate"
        elif similarity >= 0.8:
            reasoning = "High structural similarity - probable duplicate with minor changes"
        elif similarity >= 0.7:
            reasoning = "Moderate structural similarity - possible duplicate or similar pattern"
        else:
            reasoning = "Low structural similarity - may share common patterns"
        
        # Define limitations
        limitations = [
            "Analysis based on structure only",
            "Semantic equivalence not verified",
            "May miss logically similar but structurally different code"
        ]
        
        return DuplicateAnalysisResult(
            code_record_1=record1,
            code_record_2=record2,
            similarity_score=similarity,
            confidence_level=confidence,
            analysis_method=self.get_method(),
            reasoning=reasoning,
            limitations=limitations,
            metadata={
                "detection_method": "ast_simhash",
                "threshold_used": threshold
            }
        )