"""
Trivial code pattern filter for OOPStracker.

This module re-exports the refactored components for backward compatibility.
The actual implementation has been split into multiple modules in the trivial_filter package.
"""

# Re-export all components for backward compatibility
from .trivial_filter.config import TrivialFilterConfig
from .trivial_filter.analyzer import TrivialPatternAnalyzer
from .trivial_filter.filter import TrivialPatternFilter

__all__ = [
    'TrivialFilterConfig',
    'TrivialPatternAnalyzer',
    'TrivialPatternFilter',
]