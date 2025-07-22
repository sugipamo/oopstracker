"""
Detection strategy - Unified interface for different detection methods.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

from .models import CodeUnit


class ConfidenceLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class DetectionResult:
    """Unified result from any detection method."""
    is_duplicate: bool
    similarity_score: float
    confidence: ConfidenceLevel
    method_used: str
    similar_units: List[CodeUnit]
    reasoning: Optional[str] = None


class DetectionStrategy(ABC):
    """Abstract strategy for code similarity detection."""
    
    @abstractmethod
    def detect_similarity(self, code_unit: CodeUnit, candidates: List[CodeUnit]) -> DetectionResult:
        """Detect similarity between code unit and candidates."""
        pass
    
    @abstractmethod
    def get_method_name(self) -> str:
        """Get the name of this detection method."""
        pass