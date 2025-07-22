"""
AI Analysis interface and data classes.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union


@dataclass
class AnalysisRequest:
    """Request for AI analysis."""
    request_type: str  # 'similarity', 'classification', 'intent_analysis'
    content: Union[str, List[str]]
    context: Optional[Dict[str, Any]] = None
    timeout: Optional[float] = None  # Use LLM-Providers default
    temperature: float = 0.1


@dataclass 
class AnalysisResponse:
    """Response from AI analysis."""
    success: bool
    result: Any
    confidence: float
    reasoning: str
    metadata: Dict[str, Any]
    processing_time: float


class AIAnalysisInterface(ABC):
    """
    Interface for AI analysis operations.
    
    This defines the contract that all AI analysis implementations must follow.
    """
    
    @abstractmethod
    async def analyze_similarity(self, code1: str, code2: str, **kwargs) -> AnalysisResponse:
        """Analyze similarity between two code snippets."""
        pass
    
    @abstractmethod
    async def classify_function(self, code: str, categories: List[str], **kwargs) -> AnalysisResponse:
        """Classify a function into provided categories."""
        pass
    
    @abstractmethod
    async def analyze_intent(self, code: str, **kwargs) -> AnalysisResponse:
        """Analyze the intent of code."""
        pass
    
    @property
    @abstractmethod
    def available(self) -> bool:
        """Check if AI analysis is available."""
        pass