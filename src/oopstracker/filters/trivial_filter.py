"""
Main trivial pattern filter coordinating all filtering operations.
"""

import ast
from typing import List, Optional
from ..models import CodeRecord
from .config import TrivialFilterConfig
from .analyzers import TrivialPatternAnalyzer
from .rules import TrivialFilterRules


class TrivialPatternFilter:
    """Filters out trivial code patterns from duplicate detection."""
    
    def __init__(self, config: Optional[TrivialFilterConfig] = None, include_tests: bool = False):
        self.config = config or TrivialFilterConfig()
        self.include_tests = include_tests
        self.analyzer = TrivialPatternAnalyzer()
        self.rules = TrivialFilterRules(self.config)
        self._exclusion_reasons = {}
    
    def should_exclude_code_record(self, record: CodeRecord) -> bool:
        """
        Check if a CodeRecord should be excluded as trivial.
        
        Args:
            record: The CodeRecord to check
            
        Returns:
            True if the record should be excluded, False otherwise
        """
        # Skip test functions unless explicitly included
        if not self.include_tests and self._is_test_function_name(record.function_name):
            self._exclusion_reasons[record.code_hash] = "test_function"
            return True
        
        try:
            tree = ast.parse(record.source_code)
        except SyntaxError:
            # If we can't parse it, we can't filter it
            return False
        
        # Check each node in the AST
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if self._should_exclude_function(node):
                    self._exclusion_reasons[record.code_hash] = f"trivial_function:{node.name}"
                    return True
            elif isinstance(node, ast.ClassDef):
                if self._should_exclude_class(node):
                    self._exclusion_reasons[record.code_hash] = f"trivial_class:{node.name}"
                    return True
        
        return False
    
    def _is_test_function_name(self, function_name: str) -> bool:
        """Check if a function name indicates it's a test function."""
        if not function_name:
            return False
            
        test_patterns = [
            # Standard test patterns
            lambda name: name.startswith('test_'),
            lambda name: name.startswith('Test'),
            lambda name: name.endswith('_test'),
            lambda name: name.endswith('Test'),
            
            # Setup/teardown patterns
            lambda name: name in ['setUp', 'tearDown', 'setup', 'teardown'],
            lambda name: name.startswith('setup_'),
            lambda name: name.startswith('teardown_'),
            lambda name: name == 'setUpClass',
            lambda name: name == 'tearDownClass',
            lambda name: name == 'setup_method',
            lambda name: name == 'teardown_method',
            lambda name: name == 'setup_function', 
            lambda name: name == 'teardown_function',
            
            # Pytest fixtures
            lambda name: name.startswith('pytest_'),
            lambda name: name in ['conftest', 'fixture'],
            
            # Assertion helpers
            lambda name: name.startswith('assert_'),
            lambda name: name.startswith('check_'),
            
            # Mock/patch helpers
            lambda name: name.startswith('mock_'),
            lambda name: name.startswith('patch_'),
        ]
        
        return any(pattern(function_name) for pattern in test_patterns)
    
    def _should_exclude_function(self, node: ast.FunctionDef) -> bool:
        """Check if a function should be excluded based on patterns."""
        analysis = self.analyzer.analyze_function(node)
        
        # Apply filtering rules
        if self.rules.is_single_return_function(analysis):
            return True
        
        if self.rules.is_simple_special_method(analysis):
            return True
            
        if self.rules.is_simple_property(analysis):
            return True
            
        if self.rules.is_short_function(analysis):
            return True
            
        if self.rules.is_simple_converter(analysis):
            return True
        
        return False
    
    def _should_exclude_class(self, node: ast.ClassDef) -> bool:
        """Check if a class should be excluded based on patterns."""
        analysis = self.analyzer.analyze_class(node)
        
        if self.rules.is_trivial_class(analysis):
            return True
            
        if self.rules.is_data_model_class(analysis, node):
            return True
        
        return False
    
    def filter_records(self, records: List[CodeRecord]) -> List[CodeRecord]:
        """
        Filter a list of CodeRecords, removing trivial patterns.
        
        Args:
            records: List of CodeRecords to filter
            
        Returns:
            Filtered list with trivial patterns removed
        """
        return [
            record for record in records
            if not self.should_exclude_code_record(record)
        ]
    
    def get_exclusion_stats(self, records: List[CodeRecord]) -> dict:
        """
        Get statistics about what was excluded and why.
        
        Args:
            records: Original list of records before filtering
            
        Returns:
            Dictionary with exclusion statistics
        """
        total = len(records)
        filtered = self.filter_records(records)
        excluded = total - len(filtered)
        
        # Count exclusion reasons
        reason_counts = {}
        for reason in self._exclusion_reasons.values():
            category = reason.split(':')[0]
            reason_counts[category] = reason_counts.get(category, 0) + 1
        
        return {
            'total_records': total,
            'excluded_records': excluded,
            'included_records': len(filtered),
            'exclusion_rate': excluded / total if total > 0 else 0,
            'exclusion_reasons': reason_counts
        }