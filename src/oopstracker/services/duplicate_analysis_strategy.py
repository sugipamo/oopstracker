"""Abstract interface and strategies for duplicate analysis."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from ..models import CodeRecord


class AnalysisConfidenceLevel(Enum):
    """Confidence levels for analysis results."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class AnalysisMethod(Enum):
    """Available analysis methods."""
    SEMANTIC_LLM = "semantic_llm"
    STRUCTURAL_AST = "structural_ast"
    HYBRID = "hybrid"
    RULE_BASED = "rule_based"


@dataclass
class DuplicateAnalysisResult:
    """Unified result structure for duplicate analysis."""
    code_record_1: CodeRecord
    code_record_2: CodeRecord
    similarity_score: float
    confidence_level: AnalysisConfidenceLevel
    analysis_method: AnalysisMethod
    reasoning: str
    limitations: List[str]
    metadata: Dict[str, Any]


@dataclass
class AnalysisContext:
    """Context information for strategy selection."""
    requires_semantic: bool = False
    max_processing_time: Optional[float] = None
    code_complexity: Optional[str] = None  # "low", "medium", "high"
    available_resources: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.available_resources is None:
            self.available_resources = {}


class DuplicateAnalysisStrategy(ABC):
    """Abstract base class for duplicate analysis strategies."""
    
    @abstractmethod
    async def analyze(
        self,
        code_records: List[CodeRecord],
        threshold: float = 0.7
    ) -> List[DuplicateAnalysisResult]:
        """Analyze code records for duplicates.
        
        Args:
            code_records: List of code records to analyze
            threshold: Similarity threshold for duplicate detection
            
        Returns:
            List of duplicate analysis results
        """
        pass
    
    @abstractmethod
    def get_method(self) -> AnalysisMethod:
        """Get the analysis method used by this strategy."""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Get capabilities and limitations of this strategy."""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this strategy is available for use."""
        pass
    
    @abstractmethod
    def is_applicable(self, context: AnalysisContext) -> bool:
        """Check if this strategy is applicable for the given context.
        
        Args:
            context: Analysis context with requirements
            
        Returns:
            True if strategy can handle the context requirements
        """
        pass


class QualityEnhancer(ABC):
    """Abstract base class for enhancing analysis quality."""
    
    @abstractmethod
    async def enhance(
        self, 
        result: DuplicateAnalysisResult
    ) -> DuplicateAnalysisResult:
        """Enhance the quality of an analysis result.
        
        Args:
            result: Original analysis result
            
        Returns:
            Enhanced analysis result
        """
        pass


class ConfidenceCalculator:
    """Calculate confidence scores based on multiple factors."""
    
    def calculate_confidence(
        self,
        similarity_score: float,
        analysis_method: AnalysisMethod,
        additional_signals: Dict[str, Any] = None
    ) -> AnalysisConfidenceLevel:
        """Calculate confidence level for analysis result.
        
        Args:
            similarity_score: Base similarity score
            analysis_method: Method used for analysis
            additional_signals: Additional quality signals (optional)
            
        Returns:
            Confidence level
        """
        if additional_signals is None:
            additional_signals = {}
            
        # Base confidence on similarity score
        if similarity_score >= 0.9:
            base_confidence = AnalysisConfidenceLevel.HIGH
        elif similarity_score >= 0.7:
            base_confidence = AnalysisConfidenceLevel.MEDIUM
        elif similarity_score >= 0.5:
            base_confidence = AnalysisConfidenceLevel.LOW
        else:
            base_confidence = AnalysisConfidenceLevel.UNCERTAIN
        
        # Method-specific confidence adjustments
        confidence_adjustments = {
            AnalysisMethod.SEMANTIC_LLM: 0,  # No adjustment - highest confidence
            AnalysisMethod.HYBRID: 0,         # No adjustment - good confidence
            AnalysisMethod.STRUCTURAL_AST: -1,  # Reduce by one level
            AnalysisMethod.RULE_BASED: -2      # Reduce by two levels
        }
        
        adjustment = confidence_adjustments.get(analysis_method, -1)
        
        # Apply adjustment
        confidence_levels = [
            AnalysisConfidenceLevel.HIGH,
            AnalysisConfidenceLevel.MEDIUM,
            AnalysisConfidenceLevel.LOW,
            AnalysisConfidenceLevel.UNCERTAIN
        ]
        
        current_index = confidence_levels.index(base_confidence)
        adjusted_index = min(len(confidence_levels) - 1, current_index - adjustment)
        
        return confidence_levels[adjusted_index]