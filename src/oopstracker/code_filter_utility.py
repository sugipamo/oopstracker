"""
Unified code filtering utility for OOPStracker.
Centralizes all code exclusion logic for consistency and maintainability.
"""

import ast
import logging
from typing import Set, Optional, Dict, Any
from .models import CodeRecord


logger = logging.getLogger(__name__)


class CodeFilterUtility:
    """Unified utility for filtering code records based on various criteria."""
    
    # Centralized special methods definition
    SPECIAL_METHODS = {
        # Core lifecycle methods
        '__init__', '__new__', '__del__',
        
        # String representation methods
        '__str__', '__repr__', '__format__',
        
        # Comparison methods
        '__eq__', '__ne__', '__lt__', '__le__', '__gt__', '__ge__', '__hash__',
        
        # Type conversion methods
        '__bool__', '__int__', '__float__', '__complex__', '__bytes__',
        
        # Container methods
        '__len__', '__iter__', '__next__', '__reversed__',
        '__getitem__', '__setitem__', '__delitem__', '__contains__',
        
        # Context manager methods
        '__enter__', '__exit__',
        
        # Attribute access methods
        '__getattr__', '__setattr__', '__delattr__', '__getattribute__',
        
        # Callable and descriptor methods
        '__call__', '__get__', '__set__', '__delete__',
        
        # Copy methods
        '__copy__', '__deepcopy__'
    }
    
    # Centralized test function patterns
    TEST_PATTERNS = [
        'test_',           # test_something
        '_test',           # something_test  
        'Test',            # TestSomething (class names)
        'unittest',        # unittest methods
        'should_',         # should_do_something (BDD style)
    ]
    
    def __init__(self, include_tests: bool = False, include_trivial: bool = False):
        """
        Initialize code filter utility.
        
        Args:
            include_tests: Whether to include test functions and classes
            include_trivial: Whether to include trivial code patterns
        """
        self.include_tests = include_tests
        self.include_trivial = include_trivial
        
    def should_exclude_record(self, record: CodeRecord) -> bool:
        """
        Central method to determine if a code record should be excluded.
        
        Args:
            record: Code record to evaluate
            
        Returns:
            True if the record should be excluded from analysis
        """
        if not record or not record.code_content:
            return True
            
        function_name = record.function_name or ''
        
        # 1. Test function exclusion (if tests not included)
        if not self.include_tests and self._is_test_function(function_name):
            logger.debug(f"Excluding test function: {function_name}")
            return True
            
        # 2. Trivial pattern exclusion (if trivial not included)
        if not self.include_trivial:
            if self._is_trivial_code(record):
                logger.debug(f"Excluding trivial code: {function_name}")
                return True
                
        return False
        
    def _is_test_function(self, function_name: str) -> bool:
        """Check if a function name indicates it's a test function."""
        if not function_name:
            return False
            
        function_lower = function_name.lower()
        
        # Check basic patterns
        for pattern in self.TEST_PATTERNS:
            if pattern.lower() in function_lower:
                return True
                
        # Check BDD style patterns more precisely to avoid __init__ false positives
        if function_lower.startswith('it_'):  # it_should_do_something (must start with it_)
            return True
            
        return False
        
    def _is_trivial_code(self, record: CodeRecord) -> bool:
        """Check if code record represents trivial code patterns."""
        function_name = record.function_name or ''
        
        # Special method check
        if self.is_special_method(function_name):
            complexity = self._analyze_code_complexity(record.code_content)
            return self._is_simple_special_method(function_name, complexity)
            
        # Other trivial patterns can be added here
        # - Single return statements
        # - Simple property getters/setters
        # - Pass-only classes
        
        return False
        
    def is_special_method(self, function_name: str) -> bool:
        """
        Check if a function name is a special method.
        
        Args:
            function_name: Name of the function
            
        Returns:
            True if it's a special method
        """
        return (function_name.startswith('__') and 
                function_name.endswith('__') and 
                function_name in self.SPECIAL_METHODS)
                
    def _is_simple_special_method(self, function_name: str, complexity: Dict[str, Any]) -> bool:
        """Check if a special method is simple enough to be considered trivial."""
        if function_name == '__init__':
            # __init__ methods can be more complex but still commonly trivial
            return complexity.get('statement_count', 0) <= 10
        else:
            # Other special methods should be simple
            return complexity.get('statement_count', 0) <= 3
            
    def _analyze_code_complexity(self, code_content: str) -> Dict[str, Any]:
        """
        Analyze code complexity for filtering decisions.
        
        Args:
            code_content: Source code to analyze
            
        Returns:
            Dictionary with complexity metrics
        """
        try:
            # Normalize indentation for parsing
            lines = code_content.splitlines()
            if lines:
                # Remove common leading whitespace
                import textwrap
                normalized_code = textwrap.dedent(code_content)
                tree = ast.parse(normalized_code)
                
                # Find function definition
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        return self._analyze_function_node(node)
                        
        except (SyntaxError, ValueError) as e:
            logger.debug(f"Failed to parse code for complexity analysis: {e}")
            
        # Fallback: simple line-based analysis
        return {
            'statement_count': len([line for line in code_content.splitlines() 
                                  if line.strip() and not line.strip().startswith('#')]),
            'parse_error': True
        }
        
    def _analyze_function_node(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """Analyze a function AST node for complexity metrics."""
        statement_count = 0
        
        # Count various statement types
        for child in ast.walk(node):
            if isinstance(child, (ast.Assign, ast.AugAssign, ast.If, ast.For, 
                                ast.While, ast.Try, ast.With, ast.Raise, ast.Assert)):
                statement_count += 1
                
        return {
            'statement_count': statement_count,
            'has_decorator': len(node.decorator_list) > 0,
            'arg_count': len(node.args.args),
            'parse_error': False
        }