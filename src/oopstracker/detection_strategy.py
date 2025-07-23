"""
Unified detection strategy interface.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities.code_record import CodeRecord
from ..value_objects.similarity_result import SimilarityResult


class DetectionStrategy(ABC):
    """Abstract base class for duplicate detection strategies."""
    
    @abstractmethod
    def detect_duplicates(self, records: List[CodeRecord]) -> List[SimilarityResult]:
        """Detect duplicate code records."""
        pass
    
    @abstractmethod
    def find_similar(self, source_code: str, threshold: float = 0.7) -> SimilarityResult:
        """Find similar code to the given source."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return the name of this detection strategy."""
        pass


class SimHashDetectionStrategy(DetectionStrategy):
    """SimHash-based duplicate detection strategy."""
    
    def __init__(self, threshold: int = 3):
        self.threshold = threshold
    
    def detect_duplicates(self, records: List[CodeRecord]) -> List[SimilarityResult]:
        """Detect duplicates using SimHash algorithm."""
        # Implementation will be migrated from existing simhash_detector.py
        return []
    
    def find_similar(self, source_code: str, threshold: float = 0.7) -> SimilarityResult:
        """Find similar code using SimHash."""
        from ..value_objects.similarity_result import SimilarityResult
        return SimilarityResult(
            is_duplicate=False,
            similarity_score=0.0,
            matched_records=[],
            analysis_method="simhash",
            threshold=threshold
        )
    
    def get_strategy_name(self) -> str:
        return "simhash"


class SemanticDetectionStrategy(DetectionStrategy):
    """Semantic-based duplicate detection strategy."""
    
    def __init__(self, model_threshold: float = 0.8):
        self.model_threshold = model_threshold
    
    def detect_duplicates(self, records: List[CodeRecord]) -> List[SimilarityResult]:
        """Detect duplicates using semantic analysis."""
        # Implementation will be migrated from existing semantic_detector.py
        return []
    
    def find_similar(self, source_code: str, threshold: float = 0.7) -> SimilarityResult:
        """Find similar code using semantic analysis."""
        from ..value_objects.similarity_result import SimilarityResult
        return SimilarityResult(
            is_duplicate=False,
            similarity_score=0.0,
            matched_records=[],
            analysis_method="semantic",
            threshold=threshold
        )
    
    def get_strategy_name(self) -> str:
        return "semantic"


class UnifiedDetector:
    """Facade for unified duplicate detection."""
    
    def __init__(self, strategy: DetectionStrategy):
        self.strategy = strategy
    
    def detect_duplicates(self, records: List[CodeRecord]) -> List[SimilarityResult]:
        """Detect duplicates using the configured strategy."""
        return self.strategy.detect_duplicates(records)
    
    def find_similar(self, source_code: str, threshold: float = 0.7) -> SimilarityResult:
        """Find similar code using the configured strategy."""
        return self.strategy.find_similar(source_code, threshold)
    
    def switch_strategy(self, new_strategy: DetectionStrategy):
        """Switch to a different detection strategy."""
        self.strategy = new_strategy