"""Test cases for Code Analyzer following TDD principles."""

import ast
import pytest
from oopstracker.core.analyzer.code_analyzer import CodeAnalyzer


class TestCodeAnalyzer:
    """Test cases for CodeAnalyzer class."""

    def test_analyze_empty_code(self):
        """Test analyzing empty code."""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze("")
        
        assert result is not None
        assert "ast" in result
        assert "metrics" in result
        assert "features" in result

    def test_analyze_simple_function(self):
        """Test analyzing a simple function."""
        code = '''
def hello():
    print("Hello, world!")
'''
        analyzer = CodeAnalyzer()
        result = analyzer.analyze(code)
        
        assert result["ast"] is not None
        assert isinstance(result["ast"], ast.Module)
        assert "functions" in result["features"]
        assert len(result["features"]["functions"]) == 1
        assert result["features"]["functions"][0] == "hello"

    def test_analyze_class_definition(self):
        """Test analyzing a class definition."""
        code = '''
class MyClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
'''
        analyzer = CodeAnalyzer()
        result = analyzer.analyze(code)
        
        assert "classes" in result["features"]
        assert len(result["features"]["classes"]) == 1
        assert result["features"]["classes"][0] == "MyClass"
        assert "methods" in result["features"]
        assert "__init__" in result["features"]["methods"]
        assert "get_value" in result["features"]["methods"]

    def test_analyze_imports(self):
        """Test analyzing import statements."""
        code = '''
import os
from typing import List, Dict
import numpy as np
'''
        analyzer = CodeAnalyzer()
        result = analyzer.analyze(code)
        
        assert "imports" in result["features"]
        assert "os" in result["features"]["imports"]
        assert "typing" in result["features"]["imports"]
        assert "numpy" in result["features"]["imports"]

    def test_analyze_metrics(self):
        """Test code metrics calculation."""
        code = '''
def complex_function(x, y):
    if x > 0:
        if y > 0:
            return x + y
        else:
            return x - y
    else:
        return 0
'''
        analyzer = CodeAnalyzer()
        result = analyzer.analyze(code)
        
        assert "loc" in result["metrics"]  # Lines of code
        assert "complexity" in result["metrics"]  # Cyclomatic complexity
        assert result["metrics"]["loc"] > 0
        assert result["metrics"]["complexity"] > 1

    def test_analyze_syntax_error(self):
        """Test handling of syntax errors."""
        code = '''
def broken_function(
    print("This is broken"
'''
        analyzer = CodeAnalyzer()
        result = analyzer.analyze(code)
        
        assert result is not None
        assert "error" in result
        assert isinstance(result["error"], str)

    def test_analyze_variables(self):
        """Test variable detection."""
        code = '''
global_var = 100

def function():
    local_var = 200
    another_var = local_var + global_var
    return another_var
'''
        analyzer = CodeAnalyzer()
        result = analyzer.analyze(code)
        
        assert "variables" in result["features"]
        assert "global_var" in result["features"]["variables"]

    def test_analyze_decorators(self):
        """Test decorator detection."""
        code = '''
@property
def my_property(self):
    return self._value

@staticmethod
def static_method():
    return 42
'''
        analyzer = CodeAnalyzer()
        result = analyzer.analyze(code)
        
        assert "decorators" in result["features"]
        assert "property" in result["features"]["decorators"]
        assert "staticmethod" in result["features"]["decorators"]

    def test_analyze_control_flow(self):
        """Test control flow detection."""
        code = '''
def control_flow_example(items):
    for item in items:
        if item > 0:
            continue
        elif item < 0:
            break
        else:
            pass
    
    while True:
        try:
            do_something()
        except Exception:
            break
'''
        analyzer = CodeAnalyzer()
        result = analyzer.analyze(code)
        
        assert "control_flow" in result["features"]
        assert "for" in result["features"]["control_flow"]
        assert "if" in result["features"]["control_flow"]
        assert "while" in result["features"]["control_flow"]
        assert "try" in result["features"]["control_flow"]

    def test_analyze_nested_structures(self):
        """Test nested structure analysis."""
        code = '''
class OuterClass:
    class InnerClass:
        def inner_method(self):
            def nested_function():
                return 42
            return nested_function()
'''
        analyzer = CodeAnalyzer()
        result = analyzer.analyze(code)
        
        assert "classes" in result["features"]
        assert "OuterClass" in result["features"]["classes"]
        assert "InnerClass" in result["features"]["classes"]
        assert "nesting_depth" in result["metrics"]
        assert result["metrics"]["nesting_depth"] > 2

    def test_extract_features_for_similarity(self):
        """Test feature extraction for similarity comparison."""
        code = '''
def calculate_sum(a, b):
    return a + b
'''
        analyzer = CodeAnalyzer()
        features = analyzer.extract_features(code)
        
        assert isinstance(features, list)
        assert len(features) > 0
        assert any("calculate_sum" in f for f in features)
        assert any("return" in f for f in features)

    def test_get_feature_weights(self):
        """Test feature weight calculation."""
        code = '''
class ImportantClass:
    def critical_method(self):
        return self.important_value
'''
        analyzer = CodeAnalyzer()
        result = analyzer.analyze(code)
        features = analyzer.extract_features(code)
        weights = analyzer.get_feature_weights(features, result)
        
        assert isinstance(weights, list)
        assert len(weights) == len(features)
        assert all(w > 0 for w in weights)

    def test_normalize_code(self):
        """Test code normalization."""
        code = '''
def    messy_function(  x,y   ):
        return   x+y  # Comment
'''
        analyzer = CodeAnalyzer()
        normalized = analyzer.normalize_code(code)
        
        assert normalized is not None
        assert "messy_function" in normalized
        # Should remove extra whitespace but preserve structure
        assert normalized != code