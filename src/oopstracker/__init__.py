"""
OOPStracker: AI Agent Code Loop Detection and Prevention Library

A lightweight Python library for detecting and preventing code duplication
in AI agent-generated code, helping to avoid infinite loops and redundant
code generation.
"""

__version__ = "0.1.0"
__author__ = "EvoCode Team"
__email__ = "info@evocoder.ai"
__license__ = "MIT"

from .core import CodeMemory
from .models import CodeRecord, SimilarityResult
from .exceptions import OOPSTrackerError, DatabaseError, ValidationError
from .simhash_detector import SimHashSimilarityDetector, BKTree
from .hybrid_detector import HybridCodeMemory, HybridResult, create_hybrid_memory
from .refactoring_analyzer import RefactoringAnalyzer, RefactoringRecommendation, RefactoringType

__all__ = [
    "CodeMemory",
    "SimHashSimilarityDetector",
    "BKTree",
    "CodeRecord",
    "SimilarityResult",
    "OOPSTrackerError",
    "DatabaseError",
    "ValidationError",
    "HybridCodeMemory",
    "HybridResult",
    "create_hybrid_memory",
    "RefactoringAnalyzer",
    "RefactoringRecommendation",
    "RefactoringType",
]