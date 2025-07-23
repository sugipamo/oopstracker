"""
Filter modules for OOPStracker.
"""

from .trivial_filter import TrivialPatternFilter
from .config import TrivialFilterConfig
from .analyzers import TrivialPatternAnalyzer

__all__ = [
    'TrivialPatternFilter',
    'TrivialFilterConfig',
    'TrivialPatternAnalyzer'
]