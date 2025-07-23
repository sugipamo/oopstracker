"""
Trivial pattern filtering module for OOPStracker.

This module provides functionality to identify and filter out common, acceptable
code patterns that appear as duplicates but are actually appropriate.
"""

from .config import TrivialFilterConfig
from .analyzer import TrivialPatternAnalyzer
from .filter import TrivialPatternFilter
from .checkers import (
    is_single_return_function,
    is_simple_special_method,
    is_simple_property,
    is_short_function,
    is_simple_converter,
    is_trivial_class,
    is_data_model_class,
    is_test_function_name,
)

__all__ = [
    'TrivialFilterConfig',
    'TrivialPatternAnalyzer',
    'TrivialPatternFilter',
    'is_single_return_function',
    'is_simple_special_method',
    'is_simple_property',
    'is_short_function',
    'is_simple_converter',
    'is_trivial_class',
    'is_data_model_class',
    'is_test_function_name',
]