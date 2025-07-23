"""Function name analyzer for semantic classification."""

from typing import Dict, Any
from ..function_categories import FunctionCategory


class FunctionNameAnalyzer:
    """Analyzes function names to suggest taxonomy categories."""
    
    def __init__(self):
        """Initialize the name analyzer with pattern mappings."""
        self.prefix_patterns = {
            'get_': (FunctionCategory.GETTER, 0.8, "getter naming pattern"),
            'set_': (FunctionCategory.SETTER, 0.8, "setter naming pattern"),
            'test_': (FunctionCategory.TEST_FUNCTION, 0.9, "test function pattern"),
            'is_': (FunctionCategory.VALIDATION, 0.7, "boolean check pattern"),
            'has_': (FunctionCategory.VALIDATION, 0.7, "existence check pattern"),
            'can_': (FunctionCategory.VALIDATION, 0.7, "capability check pattern"),
            'should_': (FunctionCategory.VALIDATION, 0.7, "condition check pattern"),
        }
        
        self.special_names = {
            '__init__': (FunctionCategory.CONSTRUCTOR, 0.9, "constructor method"),
            '__del__': (FunctionCategory.DESTRUCTOR, 0.9, "destructor method"),
            '__str__': (FunctionCategory.CONVERSION, 0.8, "string conversion method"),
            '__repr__': (FunctionCategory.CONVERSION, 0.8, "representation method"),
        }
        
        self.keyword_patterns = {
            'validation': {
                'keywords': ['validate', 'check', 'verify', 'ensure', 'assert'],
                'category': FunctionCategory.VALIDATION,
                'confidence': 0.7,
                'indicator': "validation terminology"
            },
            'conversion': {
                'keywords': ['convert', 'transform', 'parse', 'format', 'encode', 'decode'],
                'category': FunctionCategory.CONVERSION,
                'confidence': 0.7,
                'indicator': "conversion terminology"
            },
            'business': {
                'keywords': ['process', 'handle', 'manage', 'execute', 'perform'],
                'category': FunctionCategory.BUSINESS_LOGIC,
                'confidence': 0.6,
                'indicator': "business process terminology"
            },
            'calculation': {
                'keywords': ['calculate', 'compute', 'sum', 'average', 'total'],
                'category': FunctionCategory.CALCULATION,
                'confidence': 0.7,
                'indicator': "calculation terminology"
            },
            'io': {
                'keywords': ['read', 'write', 'load', 'save', 'fetch', 'store'],
                'category': FunctionCategory.IO_OPERATION,
                'confidence': 0.7,
                'indicator': "I/O operation terminology"
            },
            'factory': {
                'keywords': ['create', 'build', 'make', 'generate', 'produce'],
                'category': FunctionCategory.FACTORY,
                'confidence': 0.7,
                'indicator': "factory pattern terminology"
            }
        }
    
    def analyze(self, function_name: str) -> Dict[str, Any]:
        """Analyze function name for semantic clues.
        
        This method now returns unknown for all cases,
        forcing the system to rely on AI classification only.
        Pattern-based analysis has been removed.
        
        Args:
            function_name: The name of the function to analyze
            
        Returns:
            Dictionary containing suggested category, confidence, and indicators
        """
        # All pattern-based analysis removed - rely on AI classification
        return self._unknown_result()
    
    def _unknown_result(self) -> Dict[str, Any]:
        """Return result for unknown pattern."""
        return {
            "suggested_category": FunctionCategory.UNKNOWN.value,
            "confidence": 0.3,
            "indicators": ["no clear naming pattern"]
        }