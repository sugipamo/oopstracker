"""Pattern-based function classification strategy.

REFACTORING NOTE: This module is extracted from FunctionTaxonomyExpert._analyze_with_patterns
for better separation of concerns. No new functionality is added - this is purely a code
reorganization to reduce the responsibilities in the main expert class.
"""

from typing import Dict, Any, Optional

from ..akinator_classifier import AkinatorClassifier


class PatternAnalysisStrategy:
    """Analyzes functions using established patterns and heuristics.
    
    This class was extracted from FunctionTaxonomyExpert._analyze_with_patterns method
    as part of the refactoring effort to separate concerns. The pattern matching logic
    remains unchanged - this is purely a code organization improvement.
    """
    
    def __init__(self):
        """Initialize pattern analysis strategy."""
        self.pattern_classifier = AkinatorClassifier()
    
    async def analyze(self, function_code: str, function_name: Optional[str] = None) -> Dict[str, Any]:
        """Analyze function using pattern matching.
        
        This method contains the exact logic from the original 
        FunctionTaxonomyExpert._analyze_with_patterns method.
        
        Args:
            function_code: Source code of the function
            function_name: Optional function name
            
        Returns:
            Analysis result with category, confidence, and reasoning
        """
        # Original logic preserved from FunctionTaxonomyExpert
        pattern_result = self.pattern_classifier.classify_function(function_code, function_name)
        
        return {
            "category": pattern_result.category,
            "confidence": pattern_result.confidence,
            "reasoning": pattern_result.reasoning,
            "matched_patterns": pattern_result.matched_rules,
            "method": "pattern_matching"
        }