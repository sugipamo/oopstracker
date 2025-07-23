"""
Main filter class for excluding trivial code patterns.
"""

import ast
from typing import List, Optional, Dict

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import CodeRecord
from .config import TrivialFilterConfig
from .analyzer import TrivialPatternAnalyzer
from . import checkers


class TrivialPatternFilter:
    """
    Filters out trivial code patterns from duplication detection.
    Identifies and excludes common patterns that are acceptable duplicates.
    """
    
    def __init__(self, config: Optional[TrivialFilterConfig] = None, include_tests: bool = False):
        self.config = config or TrivialFilterConfig()
        self.analyzer = TrivialPatternAnalyzer()
        self.include_tests = include_tests
    
    def should_exclude_code_record(self, record) -> bool:
        """
        Determine if a code record should be excluded as trivial.
        
        Args:
            record: CodeRecord to check
            
        Returns:
            True if the record should be excluded, False otherwise
        """
        try:
            tree = ast.parse(record.code)
            
            # Get the main node (function or class)
            if not tree.body:
                return True  # Empty code
            
            node = tree.body[0]
            
            if isinstance(node, ast.FunctionDef):
                # Skip test functions if not including tests
                if not self.include_tests and checkers.is_test_function_name(node.name):
                    return True
                return self._should_exclude_function(node)
            elif isinstance(node, ast.ClassDef):
                return self._should_exclude_class(node)
            else:
                # Other top-level constructs are not filtered
                return False
                
        except (SyntaxError, ValueError):
            # If we can't parse it, don't exclude it
            return False
    
    def _should_exclude_function(self, node: ast.FunctionDef) -> bool:
        """Check if a function should be excluded."""
        analysis = self.analyzer.analyze_function(node)
        
        # Apply filters based on configuration
        if self.config.enable_single_return_filter and checkers.is_single_return_function(analysis):
            return True
        
        if self.config.enable_simple_special_method_filter and checkers.is_simple_special_method(analysis):
            return True
        
        if self.config.enable_simple_property_filter and checkers.is_simple_property(analysis):
            return True
        
        if self.config.enable_short_function_filter and checkers.is_short_function(analysis, self.config.max_trivial_lines):
            return True
        
        if self.config.enable_simple_converter_filter and checkers.is_simple_converter(analysis, self.config.converter_methods):
            return True
        
        return False
    
    def _should_exclude_class(self, node: ast.ClassDef) -> bool:
        """Check if a class should be excluded."""
        analysis = self.analyzer.analyze_class(node)
        
        if self.config.enable_trivial_class_filter:
            if checkers.is_trivial_class(analysis):
                return True
            
            # Check for data model classes
            if checkers.is_data_model_class(analysis, node):
                return True
        
        return False
    
    def filter_records(self, records: List) -> List:
        """
        Filter a list of code records, removing trivial patterns.
        
        Args:
            records: List of CodeRecord objects to filter
            
        Returns:
            Filtered list with trivial patterns removed
        """
        filtered = []
        
        for record in records:
            if not self.should_exclude_code_record(record):
                filtered.append(record)
        
        return filtered
    
    def get_exclusion_stats(self, records: List) -> Dict:
        """
        Get statistics about what was excluded and why.
        
        Args:
            records: List of CodeRecord objects to analyze
            
        Returns:
            Dictionary with exclusion statistics
        """
        stats = {
            'total': len(records),
            'excluded': 0,
            'by_type': {
                'single_return': 0,
                'simple_special_method': 0,
                'simple_property': 0,
                'short_function': 0,
                'simple_converter': 0,
                'trivial_class': 0,
                'data_model_class': 0,
                'test_function': 0,
                'parse_error': 0,
            }
        }
        
        for record in records:
            try:
                tree = ast.parse(record.code)
                if not tree.body:
                    stats['excluded'] += 1
                    continue
                
                node = tree.body[0]
                excluded = False
                
                if isinstance(node, ast.FunctionDef):
                    if not self.include_tests and checkers.is_test_function_name(node.name):
                        stats['by_type']['test_function'] += 1
                        excluded = True
                    else:
                        analysis = self.analyzer.analyze_function(node)
                        
                        if self.config.enable_single_return_filter and checkers.is_single_return_function(analysis):
                            stats['by_type']['single_return'] += 1
                            excluded = True
                        elif self.config.enable_simple_special_method_filter and checkers.is_simple_special_method(analysis):
                            stats['by_type']['simple_special_method'] += 1
                            excluded = True
                        elif self.config.enable_simple_property_filter and checkers.is_simple_property(analysis):
                            stats['by_type']['simple_property'] += 1
                            excluded = True
                        elif self.config.enable_short_function_filter and checkers.is_short_function(analysis, self.config.max_trivial_lines):
                            stats['by_type']['short_function'] += 1
                            excluded = True
                        elif self.config.enable_simple_converter_filter and checkers.is_simple_converter(analysis, self.config.converter_methods):
                            stats['by_type']['simple_converter'] += 1
                            excluded = True
                
                elif isinstance(node, ast.ClassDef):
                    analysis = self.analyzer.analyze_class(node)
                    
                    if self.config.enable_trivial_class_filter:
                        if checkers.is_trivial_class(analysis):
                            stats['by_type']['trivial_class'] += 1
                            excluded = True
                        elif checkers.is_data_model_class(analysis, node):
                            stats['by_type']['data_model_class'] += 1
                            excluded = True
                
                if excluded:
                    stats['excluded'] += 1
                    
            except (SyntaxError, ValueError):
                stats['by_type']['parse_error'] += 1
                stats['excluded'] += 1
        
        stats['included'] = stats['total'] - stats['excluded']
        stats['exclusion_rate'] = stats['excluded'] / stats['total'] if stats['total'] > 0 else 0.0
        
        return stats