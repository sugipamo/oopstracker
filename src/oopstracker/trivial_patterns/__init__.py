"""Trivial pattern detection package."""

from .pattern_analyzers import TrivialPatternAnalyzer, FunctionAnalysis
from .pattern_detectors import (
    SingleReturnDetector,
    SimpleSpecialMethodDetector,
    SimplePropertyDetector,
    ShortFunctionDetector,
    SimpleConverterDetector,
    TrivialClassDetector
)
from .trivial_filter_service import TrivialFilterService, TrivialFilterConfig

__all__ = [
    'TrivialPatternAnalyzer',
    'FunctionAnalysis', 
    'SingleReturnDetector',
    'SimpleSpecialMethodDetector',
    'SimplePropertyDetector',
    'ShortFunctionDetector',
    'SimpleConverterDetector',
    'TrivialClassDetector',
    'TrivialFilterService',
    'TrivialFilterConfig'
]