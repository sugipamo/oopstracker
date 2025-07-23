"""Abstract interface for Intent Unified facade."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class IntentUnifiedFacadeInterface(ABC):
    """Abstract interface for Intent Unified semantic analysis."""
    
    @abstractmethod
    async def __aenter__(self):
        """Async context manager entry."""
        pass
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
    
    @abstractmethod
    async def analyze_semantic_similarity(self, code1: str, code2: str, language: str = "python") -> Dict[str, Any]:
        """Analyze semantic similarity between two code fragments."""
        pass


class NullIntentUnifiedFacade(IntentUnifiedFacadeInterface):
    """Null object pattern implementation for when Intent Unified is not available."""
    
    async def __aenter__(self):
        """No-op entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """No-op exit."""
        pass
    
    async def analyze_semantic_similarity(self, code1: str, code2: str, language: str = "python") -> Dict[str, Any]:
        """Return empty result when semantic analysis is not available."""
        return {
            "similarity": 0.0,
            "confidence": 0.0,
            "method": "unavailable",
            "reasoning": "Semantic analysis not available",
            "details": {}
        }