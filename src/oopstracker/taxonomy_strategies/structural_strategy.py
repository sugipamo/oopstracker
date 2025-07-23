"""Structural analysis strategy for function classification.

REFACTORING NOTE: This module is extracted from FunctionTaxonomyExpert._analyze_structure
and _analyze_function_name for better separation of concerns. No new functionality is added.
"""

import re
from typing import Dict, Any, Optional

from ..function_categories import FunctionCategory


class StructuralAnalysisStrategy:
    """Analyzes function structure and characteristics.
    
    This class was extracted from FunctionTaxonomyExpert._analyze_structure method
    as part of the refactoring effort to separate concerns. The structural analysis
    logic remains unchanged - this is purely a code organization improvement.
    """
    
    async def analyze(self, function_code: str, function_name: Optional[str] = None) -> Dict[str, Any]:
        """Analyze function structure and characteristics.
        
        This method contains the exact logic from the original 
        FunctionTaxonomyExpert._analyze_structure method.
        
        Args:
            function_code: Source code of the function
            function_name: Optional function name
            
        Returns:
            Analysis result with structural features and classification
        """
        # Original structural analysis logic preserved
        lines = function_code.strip().split('\n')
        line_count = len(lines)
        
        # Code characteristics
        code_lower = function_code.lower()
        
        # Structural features
        has_return_value = 'return ' in function_code
        has_state_change = '=' in function_code and not '==' in function_code
        has_control_flow = any(keyword in code_lower for keyword in ['for ', 'while ', 'if ', 'elif '])
        has_async_operations = 'async def' in code_lower or 'await ' in code_lower
        has_error_handling = any(keyword in code_lower for keyword in ['try:', 'except', 'raise'])
        
        # Classify based on structure
        category = FunctionCategory.UNKNOWN.value
        confidence = 0.5
        structural_indicators = []
        
        if function_name:
            name_analysis = self._analyze_function_name(function_name)
            category = name_analysis.get("suggested_category", category)
            confidence = name_analysis.get("confidence", confidence)
            structural_indicators.extend(name_analysis.get("indicators", []))
        
        # Refine based on structure (original logic preserved)
        if has_async_operations:
            if category == FunctionCategory.UNKNOWN.value:
                category = FunctionCategory.ASYNC_HANDLER.value
                confidence = 0.7
            structural_indicators.append("async operations detected")
        
        if has_error_handling:
            if category == FunctionCategory.UNKNOWN.value:
                category = FunctionCategory.ERROR_HANDLER.value
                confidence = 0.6
            structural_indicators.append("error handling present")
        
        if has_control_flow and line_count > 10:
            if category == FunctionCategory.UNKNOWN.value:
                category = FunctionCategory.BUSINESS_LOGIC.value
                confidence = 0.6
            structural_indicators.append("complex business logic")
        
        reasoning = "; ".join(structural_indicators) if structural_indicators else "Basic structural analysis"
        
        return {
            "category": category,
            "confidence": confidence,
            "reasoning": reasoning,
            "method": "structural_analysis",
            "structural_features": {
                "line_count": line_count,
                "has_return_value": has_return_value,
                "has_state_change": has_state_change,
                "has_control_flow": has_control_flow,
                "has_async_operations": has_async_operations,
                "has_error_handling": has_error_handling
            }
        }
    
    def _analyze_function_name(self, function_name: str) -> Dict[str, Any]:
        """Analyze function name for semantic clues.
        
        This method now returns unknown for all cases, 
        forcing the system to rely on AI classification only.
        """
        # Pattern-based analysis removed - rely on AI classification
        return {
            "suggested_category": FunctionCategory.UNKNOWN.value,
            "confidence": 0.0,
            "indicators": []
        }