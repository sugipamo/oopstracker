"""
Checker functions for identifying trivial code patterns.
"""

import ast
from typing import Dict


def is_single_return_function(analysis: Dict) -> bool:
    """
    Check if function only contains a single return statement.
    
    Examples:
        def get_value(self): return self._value
        def is_valid(self): return True
    """
    if not analysis['has_single_return']:
        return False
    
    # Single return with minimal other statements
    if analysis['statement_count'] <= 1:
        # Check if it's a simple return pattern
        if analysis['return_expressions']:
            expr_type = analysis['return_expressions'][0]
            # Simple returns like: return self.attr, return var, return constant
            if expr_type.startswith(('name:', 'attr:', 'const:')):
                return True
    
    return False


def is_simple_special_method(analysis: Dict) -> bool:
    """Check if this is a simple implementation of a special method."""
    if not analysis.get('is_special_method'):
        return False
    
    method_name = analysis['name']
    
    # Pass-only special methods are trivial
    if analysis['is_pass_only']:
        return True
    
    # Single return special methods with minimal logic
    if analysis['statement_count'] <= 2 and analysis['has_single_return']:
        return True
    
    return False


def is_simple_property(analysis: Dict) -> bool:
    """Check if this is a simple property getter/setter."""
    # Check for property decorators or property-like names
    if analysis.get('has_decorator') or analysis['name'].startswith(('get_', 'set_', 'is_', 'has_')):
        # Simple property pattern: single return statement
        if is_single_return_function(analysis):
            return True
    
    return False


def is_short_function(analysis: Dict, max_lines: int) -> bool:
    """Check if function is too short to be meaningful."""
    return analysis['actual_code_lines'] <= max_lines and analysis['statement_count'] <= 2


def is_simple_converter(analysis: Dict, converter_methods: set) -> bool:
    """Check if this is a simple converter method."""
    if analysis['name'] in converter_methods:
        # Simple converters often have single return
        return is_single_return_function(analysis)
    
    return False


def is_trivial_class(analysis: Dict) -> bool:
    """Check if class is trivial (empty or pass-only)."""
    return analysis['is_pass_only'] or (
        analysis['method_count'] == 0 and analysis['statement_count'] == 0
    )


def is_data_model_class(analysis: Dict, node: ast.ClassDef) -> bool:
    """
    Check if this is a data model class (dataclass, NamedTuple, etc.)
    that might have many similar __init__ methods.
    """
    # Check decorators
    decorators = {d.id if isinstance(d, ast.Name) else 
                  (d.attr if isinstance(d, ast.Attribute) else None) 
                  for d in node.decorator_list}
    
    # Common data model decorators
    data_decorators = {'dataclass', 'dataclasses.dataclass', 'pydantic.dataclass'}
    if decorators & data_decorators:
        return True
    
    # Check base classes for NamedTuple, TypedDict, BaseModel
    for base in node.bases:
        if isinstance(base, ast.Name):
            if base.id in ('NamedTuple', 'TypedDict', 'BaseModel'):
                return True
        elif isinstance(base, ast.Attribute):
            # typing.NamedTuple, typing.TypedDict
            if base.attr in ('NamedTuple', 'TypedDict', 'BaseModel'):
                return True
    
    # Heuristic: Classes with only __init__ and simple attributes
    if analysis['method_count'] <= 2:
        # Check if methods are just __init__ and maybe __repr__/__str__
        init_count = 0
        special_count = 0
        
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                if child.name == '__init__':
                    init_count += 1
                elif child.name.startswith('__') and child.name.endswith('__'):
                    special_count += 1
        
        # Likely a data class if it only has __init__ and maybe one other special method
        if init_count == 1 and special_count <= 1:
            return True
    
    return False


def is_test_function_name(function_name: str) -> bool:
    """
    Check if a function name indicates it's a test function.
    Supports pytest and unittest conventions.
    """
    # Pytest convention: functions starting with 'test_'
    if function_name.startswith('test_'):
        return True
    
    # Unittest convention: methods starting with 'test' in TestCase classes
    if function_name.startswith('test') and len(function_name) > 4:
        # Check if next character after 'test' is uppercase (testSomething pattern)
        if function_name[4].isupper():
            return True
    
    # Setup and teardown methods
    test_lifecycle_methods = {
        # Pytest
        'setup_module', 'teardown_module',
        'setup_class', 'teardown_class', 
        'setup_method', 'teardown_method',
        'setup_function', 'teardown_function',
        'setup', 'teardown',
        
        # Unittest  
        'setUp', 'tearDown',
        'setUpClass', 'tearDownClass',
        'setUpModule', 'tearDownModule',
        
        # Common test helpers
        'assert_equal', 'assert_true', 'assert_false',
        'assert_raises', 'assert_in', 'assert_not_in',
    }
    
    return function_name in test_lifecycle_methods