"""Proposed fix for semantic_analyzer.py to handle malformed code."""

import ast
import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class CodeValidationResult:
    """Result of code validation."""
    def __init__(self, is_valid: bool, error_message: Optional[str] = None):
        self.is_valid = is_valid
        self.error_message = error_message

def validate_code_syntax(code: str, language: str = "python") -> CodeValidationResult:
    """Validate code syntax before sending to LLM."""
    if language != "python":
        # For now, only validate Python code
        return CodeValidationResult(True)
    
    try:
        ast.parse(code)
        return CodeValidationResult(True)
    except SyntaxError as e:
        error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
        if e.text:
            error_msg += f" in '{e.text.strip()}'"
        return CodeValidationResult(False, error_msg)
    except Exception as e:
        return CodeValidationResult(False, f"Failed to parse code: {str(e)}")

def normalize_code_indentation(code: str) -> str:
    """Normalize code indentation to use spaces consistently."""
    # Replace tabs with 4 spaces
    lines = code.split('\n')
    normalized_lines = []
    
    for line in lines:
        # Replace tabs with spaces
        normalized_line = line.expandtabs(4)
        normalized_lines.append(normalized_line)
    
    return '\n'.join(normalized_lines)

# Modified _llm_semantic_analysis method
async def _llm_semantic_analysis_fixed(self, code1, code2):
    """Perform LLM-based semantic analysis with code validation."""
    
    # Validate code syntax first
    validation1 = validate_code_syntax(code1.code, code1.language)
    validation2 = validate_code_syntax(code2.code, code2.language)
    
    # If either code has syntax errors, return a special result
    if not validation1.is_valid or not validation2.is_valid:
        error_details = []
        if not validation1.is_valid:
            error_details.append(f"Code 1: {validation1.error_message}")
        if not validation2.is_valid:
            error_details.append(f"Code 2: {validation2.error_message}")
        
        return SemanticSimilarity(
            similarity_score=0.0,
            confidence=0.0,
            method=AnalysisMethod.FAILED,
            reasoning=f"Cannot analyze code with syntax errors: {'; '.join(error_details)}",
            analysis_time=0.0,
            metadata={
                "validation_errors": error_details,
                "fallback_reason": "syntax_error"
            }
        )
    
    # Normalize indentation to prevent issues
    normalized_code1 = normalize_code_indentation(code1.code)
    normalized_code2 = normalize_code_indentation(code2.code)
    
    # Create normalized code fragments
    normalized_fragment1 = CodeFragment(
        code=normalized_code1,
        language=code1.language,
        context=code1.context
    )
    normalized_fragment2 = CodeFragment(
        code=normalized_code2,
        language=code2.language,
        context=code2.context
    )
    
    # Build prompt with normalized code
    prompt = self._build_semantic_comparison_prompt(normalized_fragment1, normalized_fragment2)
    
    try:
        # Use LLM provider for semantic analysis
        response = await self._llm_provider.provider.generate(prompt)
        
        # Parse LLM response with better error handling
        similarity_data = self._parse_llm_response_improved(response.content)
        
        return SemanticSimilarity(
            similarity_score=similarity_data["similarity"],
            confidence=similarity_data["confidence"],
            method=AnalysisMethod.LLM_SEMANTIC,
            reasoning=similarity_data["reasoning"],
            analysis_time=0.0,  # Will be set by caller
            metadata={
                "llm_provider": self._llm_provider.provider_type,
                "raw_response": response.content[:500],  # Truncate for storage
                "code_normalized": True
            }
        )
        
    except Exception as e:
        self.logger.error(f"LLM semantic analysis failed: {e}")
        raise

def _parse_llm_response_improved(self, response: str) -> Dict[str, Any]:
    """Improved parsing of LLM response with better error handling."""
    
    import json
    import re
    
    try:
        # First, try to find the last complete JSON object (most likely to be the actual response)
        # Use a more specific pattern to avoid capturing example JSON
        json_pattern = r'\{[^{}]*"similarity"[^{}]*"confidence"[^{}]*"reasoning"[^{}]*\}'
        json_matches = list(re.finditer(json_pattern, response, re.DOTALL))
        
        if json_matches:
            # Take the last match (most likely the actual response, not example)
            json_str = json_matches[-1].group(0)
            
            # Clean up the JSON string
            # Remove comments if any
            json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
            json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
            
            data = json.loads(json_str)
            
            # Validate required fields
            required_fields = ["similarity", "confidence", "reasoning"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            return {
                "similarity": max(0.0, min(1.0, float(data.get("similarity", 0.0)))),
                "confidence": max(0.0, min(1.0, float(data.get("confidence", 0.0)))),
                "reasoning": str(data.get("reasoning", "No reasoning provided")),
                "details": data.get("details", {})
            }
        else:
            # No JSON found, try fallback parsing
            return self._fallback_parse_response(response)
            
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        self.logger.warning(f"Failed to parse LLM response: {e}")
        # Log the problematic response for debugging
        self.logger.debug(f"Problematic response: {response[:500]}...")
        return self._fallback_parse_response(response)

# Example of how to integrate these fixes into the existing semantic_analyzer.py:
"""
1. Add the validation functions at the module level
2. Replace the existing _llm_semantic_analysis method with _llm_semantic_analysis_fixed
3. Replace the existing _parse_llm_response method with _parse_llm_response_improved
4. Import the necessary modules (ast) if not already imported
"""

# Test the improvements
def test_improvements():
    """Test the improved code validation and parsing."""
    
    # Test code validation
    test_codes = [
        ("def hello():\n    print('Hello')", "Valid code"),
        ("def hello():\n    print('Hello')\n        print('World')", "Unexpected indent"),
        ("def hello():\n    print('Hello')\n\tprint('World')", "Mixed tabs/spaces"),
    ]
    
    print("=== Testing Code Validation ===")
    for code, description in test_codes:
        result = validate_code_syntax(code)
        print(f"\n{description}:")
        print(f"Valid: {result.is_valid}")
        if not result.is_valid:
            print(f"Error: {result.error_message}")
    
    # Test indentation normalization
    print("\n=== Testing Indentation Normalization ===")
    mixed_code = "def hello():\n    print('Hello')  # 4 spaces\n\tprint('World')  # 1 tab"
    normalized = normalize_code_indentation(mixed_code)
    print(f"Original:\n{repr(mixed_code)}")
    print(f"\nNormalized:\n{repr(normalized)}")
    
    # Verify normalized code is valid
    validation = validate_code_syntax(normalized)
    print(f"\nNormalized code valid: {validation.is_valid}")

if __name__ == "__main__":
    test_improvements()