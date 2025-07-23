"""Pattern detectors for identifying trivial code patterns."""

from abc import ABC, abstractmethod
from typing import Set
from .pattern_analyzers import FunctionAnalysis


class PatternDetector(ABC):
    """Abstract base class for pattern detectors."""
    
    @abstractmethod
    def is_trivial(self, analysis: FunctionAnalysis) -> bool:
        """Check if the analyzed function matches this trivial pattern."""
        pass


class SingleReturnDetector(PatternDetector):
    """Detects functions that only return a simple value."""
    
    def is_trivial(self, analysis: FunctionAnalysis) -> bool:
        """Check if function is a single return statement."""
        # Pass-only or no statements
        if analysis.is_pass_only or analysis.statement_count == 0:
            return True
        
        # Single return statement only
        if analysis.statement_count == 0 and analysis.return_count == 1:
            # Check if it's a simple return
            if analysis.return_expressions:
                expr = analysis.return_expressions[0]
                if expr.startswith(('var:', 'attr:', 'const:', 'none')):
                    return True
        
        # Property-like pattern: return self.something
        if (analysis.statement_count == 0 and 
            analysis.return_count == 1 and
            len(analysis.return_expressions) == 1 and
            analysis.return_expressions[0].startswith('attr:')):
            return True
        
        return False


class SimpleSpecialMethodDetector(PatternDetector):
    """Detects simple special methods like __str__, __repr__, etc."""
    
    def __init__(self, special_methods: Set[str] = None):
        self.special_methods = special_methods or {
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
    
    def is_trivial(self, analysis: FunctionAnalysis) -> bool:
        """Check if this is a simple special method."""
        if not analysis.is_special_method:
            return False
        
        if analysis.name not in self.special_methods:
            return False
        
        # Simple __init__ (just assignments or super call)
        if analysis.name == '__init__':
            # Allow up to 5 statements for __init__
            if analysis.statement_count <= 5:
                return True
        
        # Other special methods should be very simple
        if analysis.statement_count <= 2:
            return True
        
        # Single return special methods
        if analysis.statement_count == 0 and analysis.return_count == 1:
            return True
        
        return False


class SimplePropertyDetector(PatternDetector):
    """Detects simple property getter/setter methods."""
    
    def is_trivial(self, analysis: FunctionAnalysis) -> bool:
        """Check if this is a simple property method."""
        # Check if it has property decorator
        if not analysis.is_property:
            return False
        
        # Simple getter: just returns an attribute
        if (analysis.statement_count == 0 and 
            analysis.return_count == 1 and
            len(analysis.return_expressions) == 1):
            expr = analysis.return_expressions[0]
            if expr.startswith(('attr:', 'const:')):
                return True
        
        # Allow up to 2 statements for simple validation
        if analysis.statement_count <= 2 and analysis.return_count == 1:
            return True
        
        return False


class ShortFunctionDetector(PatternDetector):
    """Detects very short functions."""
    
    def __init__(self, max_lines: int = 3):
        self.max_lines = max_lines
    
    def is_trivial(self, analysis: FunctionAnalysis) -> bool:
        """Check if function is too short to be meaningful."""
        return analysis.actual_code_lines <= self.max_lines


class SimpleConverterDetector(PatternDetector):
    """Detects simple converter/transformer methods."""
    
    def __init__(self, converter_methods: Set[str] = None):
        self.converter_methods = converter_methods or {
            'to_dict', 'to_json', 'to_string', 'to_str',
            'from_dict', 'from_json', 'from_string',
            'as_dict', 'as_json', 'as_string',
            'get_dict', 'get_json', 'get_string',
        }
    
    def is_trivial(self, analysis: FunctionAnalysis) -> bool:
        """Check if this is a simple converter method."""
        if analysis.name not in self.converter_methods:
            return False
        
        # Simple converters typically have 1-3 statements
        if analysis.statement_count <= 3:
            return True
        
        # Single return converters
        if analysis.statement_count <= 1 and analysis.return_count == 1:
            return True
        
        return False


class TrivialClassDetector:
    """Detects trivial class patterns."""
    
    def is_trivial_class(self, class_node) -> bool:
        """Check if an entire class is trivial."""
        # Count non-trivial methods
        non_trivial_methods = 0
        total_methods = 0
        
        # Placeholder for now - would need full implementation
        # This would analyze all methods in the class
        return False