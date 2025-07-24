"""
Pure LLM unified detector with no pattern matching implementations.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .code_record import CodeRecord
from .similarity_result import SimilarityResult


@dataclass
class DetectionConfiguration:
    """Configuration for detection operations."""
    algorithm: str = "pure_llm"
    threshold: float = 0.7
    include_exact_matches: bool = True
    include_partial_matches: bool = True
    max_results: int = 100
    max_records_per_batch: int = 200
    memory_cleanup_interval: int = 50


class DuplicateDetector(ABC):
    """Abstract base for duplicate detection algorithms."""
    
    @abstractmethod
    def detect_duplicates(self, records: List[CodeRecord], config: DetectionConfiguration) -> List[SimilarityResult]:
        """Detect duplicate code records."""
        pass
    
    @abstractmethod
    def find_similar(self, source_code: str, records: List[CodeRecord], config: DetectionConfiguration) -> SimilarityResult:
        """Find similar code to source."""
        pass
    
    @abstractmethod
    def get_algorithm_name(self) -> str:
        """Return algorithm name."""
        pass


class UnifiedDetectionService:
    """Unified service using only pure LLM detection."""
    
    def __init__(self):
        # Import pure LLM detector - no pattern matching
        from .pure_llm_detector import PureLLMDetector
        
        self.detectors = {
            "pure_llm": PureLLMDetector()
        }
        self.default_config = DetectionConfiguration(algorithm="pure_llm")
    
    def detect_duplicates(self, records: List[CodeRecord], algorithm: str = None, config: DetectionConfiguration = None) -> List[SimilarityResult]:
        """Detect duplicates using pure LLM algorithm."""
        detector = self._get_detector(algorithm)
        detection_config = config or self.default_config
        
        return detector.detect_duplicates(records, detection_config)
    
    def find_similar(self, source_code: str, records: List[CodeRecord], algorithm: str = None, config: DetectionConfiguration = None) -> SimilarityResult:
        """Find similar code using pure LLM algorithm."""
        detector = self._get_detector(algorithm)
        detection_config = config or self.default_config
        
        return detector.find_similar(source_code, records, detection_config)
    
    def get_available_algorithms(self) -> List[str]:
        """Get list of available detection algorithms."""
        return list(self.detectors.keys())
    
    def register_detector(self, name: str, detector: DuplicateDetector):
        """Register a new detection algorithm."""
        self.detectors[name] = detector
    
    def _get_detector(self, algorithm: str = None) -> DuplicateDetector:
        """Get detector by algorithm name."""
        algo_name = algorithm or self.default_config.algorithm
        
        if algo_name not in self.detectors:
            algo_name = "pure_llm"  # fallback to pure LLM
        
        return self.detectors[algo_name]