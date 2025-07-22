"""Semantic analysis strategy using LLM for duplicate detection."""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple

from .duplicate_analysis_strategy import (
    DuplicateAnalysisStrategy,
    DuplicateAnalysisResult,
    AnalysisMethod,
    AnalysisConfidenceLevel,
    ConfidenceCalculator,
    AnalysisContext
)
from .semantic_analysis_service import (
    SemanticAnalysisService,
    SemanticDuplicateResult,
    SemanticAnalysisStatus
)
from ..models import CodeRecord


class SemanticLLMStrategy(DuplicateAnalysisStrategy):
    """Strategy for semantic code analysis using LLM."""
    
    def __init__(self, intent_unified_available: bool = True):
        """Initialize semantic LLM strategy.
        
        Args:
            intent_unified_available: Whether intent_unified service is available
        """
        self.service = SemanticAnalysisService(intent_unified_available)
        self.logger = logging.getLogger(__name__)
        self.confidence_calculator = ConfidenceCalculator()
        self._initialized = False
    
    async def analyze(
        self,
        code_records: List[CodeRecord],
        threshold: float = 0.7
    ) -> List[DuplicateAnalysisResult]:
        """Analyze code records for duplicates using semantic analysis.
        
        Args:
            code_records: List of code records to analyze
            threshold: Similarity threshold
            
        Returns:
            List of duplicate analysis results
        """
        # Ensure service is initialized
        if not self._initialized:
            await self.service.initialize()
            self._initialized = True
        
        # Generate all possible pairs for analysis
        pairs = self._generate_code_pairs(code_records)
        
        # Create candidates for semantic analysis
        candidates = [(pair[0], pair[1], 0.0) for pair in pairs]
        
        # Perform semantic analysis
        semantic_results = await self.service.analyze_duplicates(
            code_records=code_records,
            structural_candidates=candidates,
            threshold=threshold,
            max_concurrent=3
        )
        
        # Convert to unified result format
        analysis_results = []
        for sem_result in semantic_results:
            if sem_result.status == SemanticAnalysisStatus.SUCCESS:
                result = self._create_analysis_result(sem_result)
                analysis_results.append(result)
        
        return analysis_results
    
    def get_method(self) -> AnalysisMethod:
        """Get the analysis method used by this strategy."""
        return AnalysisMethod.SEMANTIC_LLM
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get capabilities and limitations of this strategy."""
        return {
            "strengths": [
                "Detects semantic equivalence",
                "Understands code intent",
                "Can identify refactored duplicates",
                "Provides detailed reasoning"
            ],
            "limitations": [
                "Requires external LLM service",
                "Slower than structural analysis",
                "May have API rate limits",
                "Costs associated with LLM usage"
            ],
            "best_for": [
                "Semantic duplicate detection",
                "Understanding code intent",
                "Complex refactoring patterns"
            ]
        }
    
    async def is_available(self) -> bool:
        """Check if this strategy is available for use."""
        if not self._initialized:
            await self.service.initialize()
            self._initialized = True
        return self.service.intent_unified_available
    
    def is_applicable(self, context: AnalysisContext) -> bool:
        """Check if this strategy is applicable for the given context.
        
        Args:
            context: Analysis context with requirements
            
        Returns:
            True if strategy can handle the context requirements
        """
        # Always applicable if semantic analysis is required
        if context.requires_semantic:
            return True
        
        # Check if LLM service is available in resources
        if context.available_resources.get('llm_service', True):
            # Good for complex code that needs semantic understanding
            if context.code_complexity in ['medium', 'high']:
                return True
            # If we have enough time, semantic analysis provides best results
            if context.max_processing_time is None or context.max_processing_time > 30.0:
                return True
        
        return False
    
    async def cleanup(self):
        """Cleanup resources."""
        if self._initialized:
            await self.service.cleanup()
            self._initialized = False
    
    def _generate_code_pairs(
        self, 
        code_records: List[CodeRecord]
    ) -> List[Tuple[CodeRecord, CodeRecord]]:
        """Generate all unique pairs of code records.
        
        Args:
            code_records: List of code records
            
        Returns:
            List of unique code record pairs
        """
        pairs = []
        for i in range(len(code_records)):
            for j in range(i + 1, len(code_records)):
                pairs.append((code_records[i], code_records[j]))
        return pairs
    
    def _create_analysis_result(
        self,
        sem_result: SemanticDuplicateResult
    ) -> DuplicateAnalysisResult:
        """Create a unified analysis result from semantic result.
        
        Args:
            sem_result: Semantic analysis result
            
        Returns:
            Unified analysis result
        """
        # Calculate confidence
        confidence = self.confidence_calculator.calculate_confidence(
            similarity_score=sem_result.semantic_similarity,
            analysis_method=self.get_method(),
            additional_signals={
                "analysis_time": sem_result.analysis_time,
                "llm_confidence": sem_result.confidence
            }
        )
        
        # Define limitations (minimal for LLM-based analysis)
        limitations = []
        if sem_result.analysis_time > 5.0:
            limitations.append("Analysis took longer than expected")
        
        return DuplicateAnalysisResult(
            code_record_1=sem_result.code_record_1,
            code_record_2=sem_result.code_record_2,
            similarity_score=sem_result.semantic_similarity,
            confidence_level=confidence,
            analysis_method=self.get_method(),
            reasoning=sem_result.reasoning,
            limitations=limitations,
            metadata={
                **sem_result.metadata,
                "analysis_time": sem_result.analysis_time,
                "original_method": sem_result.analysis_method
            }
        )