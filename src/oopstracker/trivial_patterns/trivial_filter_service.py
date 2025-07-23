"""Trivial filter service using pattern detectors."""

import ast
from typing import List, Set, Optional
from dataclasses import dataclass

from ..models import CodeRecord
from .pattern_analyzers import TrivialPatternAnalyzer
from .pattern_detectors import (
    SingleReturnDetector,
    SimpleSpecialMethodDetector,
    SimplePropertyDetector,
    ShortFunctionDetector,
    SimpleConverterDetector,
    PatternDetector
)


@dataclass
class TrivialFilterConfig:
    """Configuration for trivial pattern filtering."""
    
    # Level 1 filters (always applied)
    enable_single_return_filter: bool = True
    enable_simple_special_method_filter: bool = True
    enable_trivial_class_filter: bool = True
    enable_simple_property_filter: bool = True
    
    # Level 2 filters (configurable)
    enable_short_function_filter: bool = False
    max_trivial_lines: int = 3
    enable_simple_converter_filter: bool = False
    
    # Special method names that are commonly trivial
    special_methods: Set[str] = None
    
    # Converter method names that are often trivial
    converter_methods: Set[str] = None
    
    def __post_init__(self):
        if self.special_methods is None:
            self.special_methods = {
                '__init__', '__new__', '__del__',
                '__str__', '__repr__', '__format__',
                '__eq__', '__ne__', '__lt__', '__le__', '__gt__', '__ge__', '__hash__',
                '__bool__', '__int__', '__float__', '__complex__', '__bytes__',
                '__len__', '__iter__', '__next__', '__reversed__',
                '__getitem__', '__setitem__', '__delitem__', '__contains__',
                '__enter__', '__exit__',
                '__getattr__', '__setattr__', '__delattr__',
                '__call__',
            }
        
        if self.converter_methods is None:
            self.converter_methods = {
                'to_dict', 'to_json', 'to_string', 'to_str',
                'from_dict', 'from_json', 'from_string',
                'as_dict', 'as_json', 'as_string',
                'get_dict', 'get_json', 'get_string',
            }


class TrivialFilterService:
    """Service for filtering trivial code patterns."""
    
    def __init__(self, config: Optional[TrivialFilterConfig] = None, include_tests: bool = False):
        self.config = config or TrivialFilterConfig()
        self.include_tests = include_tests
        self.analyzer = TrivialPatternAnalyzer()
        
        # Initialize detectors based on configuration
        self.detectors: List[PatternDetector] = []
        
        if self.config.enable_single_return_filter:
            self.detectors.append(SingleReturnDetector())
        
        if self.config.enable_simple_special_method_filter:
            self.detectors.append(
                SimpleSpecialMethodDetector(self.config.special_methods)
            )
        
        if self.config.enable_simple_property_filter:
            self.detectors.append(SimplePropertyDetector())
        
        if self.config.enable_short_function_filter:
            self.detectors.append(
                ShortFunctionDetector(self.config.max_trivial_lines)
            )
        
        if self.config.enable_simple_converter_filter:
            self.detectors.append(
                SimpleConverterDetector(self.config.converter_methods)
            )
    
    def should_exclude_code_record(self, record: CodeRecord) -> bool:
        """
        Determine if a code record should be excluded from duplication detection.
        
        Args:
            record: Code record to analyze
            
        Returns:
            True if the record should be excluded
        """
        if not record.code_content:
            return True
        
        # Check if this is a test function by name (if tests not included)
        if not self.include_tests and record.function_name:
            if self._is_test_function_name(record.function_name):
                return True
        
        try:
            tree = ast.parse(record.code_content)
            
            # Find the main function or class
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if self._should_exclude_function(node):
                        return True
                elif isinstance(node, ast.ClassDef):
                    # Class filtering would go here
                    pass
            
            return False
            
        except (SyntaxError, ValueError):
            # If we can't parse it, don't exclude it
            return False
    
    def _is_test_function_name(self, function_name: str) -> bool:
        """Check if a function name indicates it's a test function."""
        if not function_name:
            return False
            
        # Check for common test function patterns
        test_patterns = [
            'test_',           # test_something
            '_test',           # something_test  
            'Test',            # TestSomething (class names)
            'unittest',        # unittest methods
            'should_',         # should_do_something (BDD style)
        ]
        
        function_lower = function_name.lower()
        
        # Check basic patterns
        if any(pattern.lower() in function_lower for pattern in test_patterns):
            return True
            
        # Check BDD style patterns more precisely
        if function_lower.startswith('it_'):  # it_should_do_something
            return True
            
        return False
    
    def _should_exclude_function(self, node: ast.FunctionDef) -> bool:
        """Check if a function should be excluded."""
        # Check if this is a test function (if tests not included)
        if not self.include_tests and self._is_test_function_name(node.name):
            return True
        
        # Analyze the function
        analysis = self.analyzer.analyze_function(node)
        
        # Check against all configured detectors
        for detector in self.detectors:
            if detector.is_trivial(analysis):
                return True
        
        return False
    
    def filter_code_records(self, records: List[CodeRecord]) -> List[CodeRecord]:
        """
        Filter out trivial code records from a list.
        
        Args:
            records: List of code records to filter
            
        Returns:
            Filtered list excluding trivial patterns
        """
        return [
            record for record in records
            if not self.should_exclude_code_record(record)
        ]