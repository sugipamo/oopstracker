"""
OOPStracker: AI Agent Code Loop Detection and Prevention Library

A lightweight Python library for detecting and preventing code duplication
in AI agent-generated code, helping to avoid infinite loops and redundant
code generation.

REFACTORED: This library has been refactored using the Centralize pattern.
Use UnifiedOOPStracker for the simplified, centralized interface.
"""

__version__ = "0.2.0"
__author__ = "EvoCode Team"
__email__ = "info@evocoder.ai"
__license__ = "MIT"

# New layered architecture (recommended)
from .application import OOPSTrackerFacade, create_oopstracker
from .services import UnifiedConfig, AnalysisConfig, DatabaseConfig

# Legacy unified interface (backward compatibility) 
from .unified_interface import UnifiedOOPStracker, AnalysisSummary

# Legacy interfaces (for backward compatibility)
from .core import CodeMemory
from .models import CodeRecord, SimilarityResult
from .exceptions import OOPSTrackerError, DatabaseError, ValidationError
from .simhash_detector import SimHashSimilarityDetector, BKTree
from .hybrid_detector import HybridCodeMemory, HybridResult, create_hybrid_memory
from .refactoring_analyzer import RefactoringAnalyzer, RefactoringRecommendation, RefactoringType

__all__ = [
    # New layered architecture (recommended)
    "OOPSTrackerFacade",
    "create_oopstracker", 
    "UnifiedConfig",
    "AnalysisConfig", 
    "DatabaseConfig",
    
    # Legacy unified interface (backward compatibility)
    "UnifiedOOPStracker",
    "AnalysisSummary",
    
    # Legacy interfaces (backward compatibility)
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