"""
Detection Strategy Bridge - Unified interface for different detection strategies.
Implements the Bridge pattern to abstract different detection implementations.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Protocol
from dataclasses import dataclass
import logging

from ..models import CodeRecord, SimilarityResult
from ..services import AnalysisConfig


@dataclass
class DetectionResult:
    """Unified result from any detection strategy."""
    is_duplicate: bool
    similarity_score: float
    similar_records: List[CodeRecord]
    confidence: float
    metadata: Dict[str, Any]
    detection_method: str


class DetectionStrategy(Protocol):
    """Protocol defining the interface for detection strategies."""
    
    def register_code(self, code: str, function_name: str, metadata: Optional[Dict[str, Any]] = None) -> CodeRecord:
        """Register code for future duplicate detection."""
        ...
    
    def is_duplicate(self, code: str) -> DetectionResult:
        """Check if code is a duplicate of registered code."""
        ...
    
    def find_similar_code(self, code: str, threshold: Optional[float] = None) -> List[CodeRecord]:
        """Find similar code records."""
        ...
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about registered code."""
        ...


class SimHashDetectionStrategy:
    """SimHash-based detection strategy implementation."""
    
    def __init__(self, threshold: int = 10):
        self.threshold = threshold
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Lazy import to avoid circular dependencies
        from ..simhash_detector import SimHashSimilarityDetector
        self._detector = SimHashSimilarityDetector(threshold=threshold)
    
    def register_code(self, code: str, function_name: str, metadata: Optional[Dict[str, Any]] = None) -> CodeRecord:
        """Register code using SimHash detector."""
        try:
            result = self._detector.register(code, function_name)
            return result
        except Exception as e:
            self.logger.error(f"SimHash registration failed: {e}")
            raise
    
    def is_duplicate(self, code: str) -> DetectionResult:
        """Check for duplicates using SimHash."""
        try:
            result = self._detector.is_duplicate(code)
            
            return DetectionResult(
                is_duplicate=result.is_duplicate if hasattr(result, 'is_duplicate') else False,
                similarity_score=result.similarity_score if hasattr(result, 'similarity_score') else 0.0,
                similar_records=result.similar_records if hasattr(result, 'similar_records') else [],
                confidence=0.95,  # SimHash has high confidence
                metadata={"threshold": self.threshold, "method": "simhash"},
                detection_method="simhash"
            )
        except Exception as e:
            self.logger.error(f"SimHash duplicate check failed: {e}")
            return DetectionResult(
                is_duplicate=False,
                similarity_score=0.0,
                similar_records=[],
                confidence=0.0,
                metadata={"error": str(e)},
                detection_method="simhash"
            )
    
    def find_similar_code(self, code: str, threshold: Optional[float] = None) -> List[CodeRecord]:
        """Find similar code using SimHash."""
        result = self.is_duplicate(code)
        return result.similar_records
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get SimHash detector statistics."""
        try:
            if hasattr(self._detector, 'get_stats'):
                stats = self._detector.get_stats()
                return {
                    "strategy": "simhash",
                    "threshold": self.threshold,
                    "registered_records": stats.get("size", 0),
                    "tree_depth": stats.get("depth", 0)
                }
            else:
                return {
                    "strategy": "simhash",
                    "threshold": self.threshold,
                    "registered_records": "unknown"
                }
        except Exception as e:
            self.logger.error(f"Failed to get SimHash statistics: {e}")
            return {
                "strategy": "simhash", 
                "error": str(e)
            }


class ASTDetectionStrategy:
    """AST-based detection strategy implementation."""
    
    def __init__(self, threshold: int = 10):
        self.threshold = threshold
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Lazy import to avoid circular dependencies
        from ..ast_simhash_detector import ASTSimHashDetector
        self._detector = ASTSimHashDetector(threshold=threshold)
    
    def register_code(self, code: str, function_name: str, metadata: Optional[Dict[str, Any]] = None) -> CodeRecord:
        """Register code using AST detector."""
        try:
            result = self._detector.register(code, function_name)
            return result
        except Exception as e:
            self.logger.error(f"AST registration failed: {e}")
            raise
    
    def is_duplicate(self, code: str) -> DetectionResult:
        """Check for duplicates using AST analysis."""
        try:
            result = self._detector.is_duplicate(code)
            
            return DetectionResult(
                is_duplicate=result.is_duplicate if hasattr(result, 'is_duplicate') else False,
                similarity_score=result.similarity_score if hasattr(result, 'similarity_score') else 0.0,
                similar_records=result.similar_records if hasattr(result, 'similar_records') else [],
                confidence=0.90,  # AST has good confidence
                metadata={"threshold": self.threshold, "method": "ast"},
                detection_method="ast"
            )
        except Exception as e:
            self.logger.error(f"AST duplicate check failed: {e}")
            return DetectionResult(
                is_duplicate=False,
                similarity_score=0.0,
                similar_records=[],
                confidence=0.0,
                metadata={"error": str(e)},
                detection_method="ast"
            )
    
    def find_similar_code(self, code: str, threshold: Optional[float] = None) -> List[CodeRecord]:
        """Find similar code using AST analysis."""
        result = self.is_duplicate(code)
        return result.similar_records
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get AST detector statistics."""
        try:
            return {
                "strategy": "ast",
                "threshold": self.threshold,
                "registered_records": "available"  # AST detector might not track this
            }
        except Exception as e:
            self.logger.error(f"Failed to get AST statistics: {e}")
            return {
                "strategy": "ast",
                "error": str(e)
            }


class HybridDetectionStrategy:
    """Hybrid detection strategy combining multiple approaches."""
    
    def __init__(self, threshold: int = 10):
        self.threshold = threshold
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize multiple strategies
        self.simhash_strategy = SimHashDetectionStrategy(threshold)
        self.ast_strategy = ASTDetectionStrategy(threshold)
        
        self.strategies = [
            ("simhash", self.simhash_strategy),
            ("ast", self.ast_strategy)
        ]
    
    def register_code(self, code: str, function_name: str, metadata: Optional[Dict[str, Any]] = None) -> CodeRecord:
        """Register code with all strategies."""
        # Primary registration with AST strategy
        primary_result = self.ast_strategy.register_code(code, function_name, metadata)
        
        # Also register with SimHash for performance
        try:
            self.simhash_strategy.register_code(code, function_name, metadata)
        except Exception as e:
            self.logger.warning(f"SimHash registration failed in hybrid mode: {e}")
        
        return primary_result
    
    def is_duplicate(self, code: str) -> DetectionResult:
        """Check for duplicates using hybrid approach."""
        results = []
        
        # Collect results from all strategies
        for name, strategy in self.strategies:
            try:
                result = strategy.is_duplicate(code)
                results.append((name, result))
            except Exception as e:
                self.logger.warning(f"Strategy {name} failed: {e}")
                continue
        
        if not results:
            return DetectionResult(
                is_duplicate=False,
                similarity_score=0.0,
                similar_records=[],
                confidence=0.0,
                metadata={"error": "All strategies failed"},
                detection_method="hybrid"
            )
        
        # Combine results using weighted average
        total_confidence = 0
        weighted_score = 0
        all_similar_records = []
        is_duplicate = False
        
        for name, result in results:
            weight = 0.7 if name == "ast" else 0.3  # Prefer AST results
            total_confidence += result.confidence * weight
            weighted_score += result.similarity_score * weight
            
            if result.is_duplicate:
                is_duplicate = True
                all_similar_records.extend(result.similar_records)
        
        # Remove duplicate records
        unique_records = []
        seen_hashes = set()
        for record in all_similar_records:
            record_hash = getattr(record, 'code_hash', str(record))
            if record_hash not in seen_hashes:
                unique_records.append(record)
                seen_hashes.add(record_hash)
        
        return DetectionResult(
            is_duplicate=is_duplicate,
            similarity_score=weighted_score,
            similar_records=unique_records,
            confidence=total_confidence,
            metadata={
                "strategies_used": [name for name, _ in results],
                "individual_results": {name: result.metadata for name, result in results}
            },
            detection_method="hybrid"
        )
    
    def find_similar_code(self, code: str, threshold: Optional[float] = None) -> List[CodeRecord]:
        """Find similar code using hybrid approach."""
        result = self.is_duplicate(code)
        return result.similar_records
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get hybrid detector statistics."""
        stats = {
            "strategy": "hybrid",
            "threshold": self.threshold,
            "component_strategies": {}
        }
        
        for name, strategy in self.strategies:
            try:
                stats["component_strategies"][name] = strategy.get_statistics()
            except Exception as e:
                stats["component_strategies"][name] = {"error": str(e)}
        
        return stats


class DetectionStrategyFactory:
    """Factory for creating detection strategies."""
    
    @staticmethod
    def create_strategy(config: AnalysisConfig) -> DetectionStrategy:
        """
        Create appropriate detection strategy based on configuration.
        
        Args:
            config: Analysis configuration
            
        Returns:
            Detection strategy instance
        """
        method = config.detection_method.value.lower()
        threshold = config.simhash_threshold
        
        if method == "simhash":
            return SimHashDetectionStrategy(threshold=threshold)
        elif method == "ast":
            return ASTDetectionStrategy(threshold=threshold)
        elif method == "hybrid":
            return HybridDetectionStrategy(threshold=threshold)
        else:
            # Default to hybrid
            logging.warning(f"Unknown detection method: {method}, using hybrid")
            return HybridDetectionStrategy(threshold=threshold)
    
    @staticmethod
    def get_available_strategies() -> List[str]:
        """Get list of available strategy names."""
        return ["simhash", "ast", "hybrid"]


# Convenience functions
def create_detection_strategy(method: str = "hybrid", threshold: int = 10) -> DetectionStrategy:
    """Create a detection strategy with simple parameters."""
    from ..services import AnalysisConfig, DetectionMethod
    
    try:
        detection_method = DetectionMethod(method.lower())
    except ValueError:
        detection_method = DetectionMethod.HYBRID
    
    config = AnalysisConfig(
        detection_method=detection_method,
        simhash_threshold=threshold
    )
    
    return DetectionStrategyFactory.create_strategy(config)