"""
Pattern generator for function classification rules.
Extracted from AkinatorClassifier to follow Single Responsibility Principle.
"""

from typing import List, Dict, Any
import re

from .classification_rules import get_pattern_keywords


class PatternGenerator:
    """Generates smart patterns for function classification."""
    
    def generate_smart_patterns(self, func_name: str, function_code: str, category: str) -> List[Dict[str, Any]]:
        """Generate smart regex patterns based on function name and category."""
        patterns = []
        
        # Extract meaningful parts from function name
        name_parts = re.split(r'_|(?=[A-Z])', func_name)
        name_parts = [p.lower() for p in name_parts if p]
        
        # Generate patterns based on category
        if category == "getter":
            patterns.extend(self._generate_getter_patterns(func_name, name_parts))
        elif category == "setter":
            patterns.extend(self._generate_setter_patterns(func_name, name_parts))
        elif category == "validator":
            patterns.extend(self._generate_validation_patterns(func_name, function_code, name_parts[-1] if name_parts else ""))
        elif category == "business_logic":
            patterns.extend(self._generate_business_logic_patterns(func_name))
        elif category == "data_processing":
            patterns.extend(self._generate_data_processing_patterns(func_name))
        
        return patterns
    
    def _generate_getter_patterns(self, func_name: str, name_parts: List[str]) -> List[Dict[str, Any]]:
        """Generate getter-specific patterns."""
        patterns = []
        
        # Pattern for function names starting with 'get'
        if name_parts and name_parts[0] == "get":
            patterns.append({
                "pattern": rf"def\s+get_?\w*{name_parts[-1] if len(name_parts) > 1 else ''}",
                "confidence": 0.9,
                "description": f"Functions named like {func_name}"
            })
        
        # Pattern for property-style getters
        patterns.append({
            "pattern": r"@property\s*\n\s*def\s+\w+",
            "confidence": 0.85,
            "description": "Property decorated getters"
        })
        
        return patterns
    
    def _generate_setter_patterns(self, func_name: str, name_parts: List[str]) -> List[Dict[str, Any]]:
        """Generate setter-specific patterns."""
        patterns = []
        
        # Pattern for function names starting with 'set'
        if name_parts and name_parts[0] == "set":
            patterns.append({
                "pattern": rf"def\s+set_?\w*{name_parts[-1] if len(name_parts) > 1 else ''}",
                "confidence": 0.9,
                "description": f"Functions named like {func_name}"
            })
        
        # Pattern for property setters
        patterns.append({
            "pattern": r"@\w+\.setter\s*\n\s*def\s+\w+",
            "confidence": 0.85,
            "description": "Property setter decorators"
        })
        
        return patterns
    
    def _generate_business_logic_patterns(self, func_name: str) -> List[Dict[str, Any]]:
        """Generate patterns for business logic functions."""
        patterns = []
        
        # Get keywords from centralized configuration
        keywords = get_pattern_keywords()
        action_words = keywords.get('business_logic', [])
        
        if any(word in func_name.lower() for word in action_words):
            pattern_words = "|".join(action_words)
            patterns.append({
                'pattern': rf"def\s+({pattern_words})_\w+\s*\(",
                'type': 'action_pattern',
                'description': f"Business logic function with action word pattern",
                'confidence': 0.75
            })
        
        return patterns
    
    def _generate_data_processing_patterns(self, func_name: str) -> List[Dict[str, Any]]:
        """Generate patterns for data processing functions."""
        patterns = []
        
        # Get keywords from centralized configuration
        keywords = get_pattern_keywords()
        data_words = keywords.get('data_processing', [])
        
        if any(word in func_name.lower() for word in data_words):
            pattern_words = "|".join(data_words)
            patterns.append({
                'pattern': rf"def\s+({pattern_words})\w*\s*\(",
                'type': 'data_pattern',
                'description': f"Data processing function pattern",
                'confidence': 0.8
            })
        
        return patterns
    
    def _generate_validation_patterns(self, func_name: str, function_code: str, last_part: str) -> List[Dict[str, Any]]:
        """Generate patterns for validation functions."""
        patterns = []
        
        # Look for validation prefixes
        if func_name.startswith(("validate", "check", "verify", "is_", "has_", "can_")):
            patterns.append({
                "pattern": rf"def\s+(?:validate|check|verify|is_|has_|can_)\w*{last_part}",
                "confidence": 0.85,
                "description": f"Validation functions like {func_name}"
            })
        
        # Look for validation patterns in code
        if "raise" in function_code and any(exc in function_code for exc in ["Error", "Exception"]):
            patterns.append({
                "pattern": r"def\s+\w+.*\n(?:.*\n)*.*raise\s+\w*(?:Error|Exception)",
                "confidence": 0.7,
                "description": "Functions that raise validation errors"
            })
        
        # Boolean return validation
        if "return True" in function_code or "return False" in function_code:
            patterns.append({
                "pattern": r"def\s+(?:is_|has_|can_|check_)\w+.*\n(?:.*\n)*.*return\s+(?:True|False)",
                "confidence": 0.75,
                "description": "Boolean validation functions"
            })
        
        # Type checking patterns
        if "isinstance" in function_code:
            patterns.append({
                "pattern": r"def\s+\w+.*\n(?:.*\n)*.*isinstance\s*\(",
                "confidence": 0.7,
                "description": "Type validation functions"
            })
        
        # Range/bounds checking
        if any(op in function_code for op in ["<", ">", "<=", ">=", "in range"]):
            patterns.append({
                "pattern": r"def\s+\w+.*\n(?:.*\n)*.*(?:[<>]=?|in\s+range)",
                "confidence": 0.65,
                "description": "Range validation functions"
            })
        
        # Pattern matching
        if "re.match" in function_code or "re.search" in function_code:
            patterns.append({
                "pattern": r"def\s+\w+.*\n(?:.*\n)*.*re\.(?:match|search)",
                "confidence": 0.7,
                "description": "Pattern validation functions"
            })
        
        # Length validation
        if "len(" in function_code:
            patterns.append({
                "pattern": r"def\s+\w+.*\n(?:.*\n)*.*len\s*\(",
                "confidence": 0.6,
                "description": "Length validation functions"
            })
        
        # Required field validation
        if any(check in function_code for check in ["is None", "is not None", "== None", "!= None"]):
            patterns.append({
                "pattern": r"def\s+\w+.*\n(?:.*\n)*.*(?:is\s+(?:not\s+)?None|[!=]=\s*None)",
                "confidence": 0.65,
                "description": "Null validation functions"
            })
        
        # Schema validation
        if any(term in function_code for term in ["schema", "validate", "required"]):
            patterns.append({
                "pattern": r"def\s+\w+.*\n(?:.*\n)*.*(?:schema|validate|required)",
                "confidence": 0.7,
                "description": "Schema validation functions"
            })
        
        return patterns