#!/usr/bin/env python3
"""
Centralized LLM Prompt Handler for consistent response formatting.

This module applies the Centralize refactor pattern to unify all LLM prompt
handling and response parsing across the application.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .ai_analysis_coordinator import AnalysisResponse


@dataclass
class ParsedLLMResponse:
    """Parsed LLM response with structured data."""
    pattern: Optional[str] = None
    reasoning: Optional[str] = None
    purpose: Optional[str] = None
    functionality: Optional[str] = None
    classification: Optional[str] = None
    confidence: float = 0.0
    raw_response: str = ""
    group_a_name: Optional[str] = None
    group_b_name: Optional[str] = None


class LLMPromptHandler:
    """
    Centralized handler for LLM prompts and response parsing.
    
    Applies Centralize pattern to consolidate all LLM interaction logic
    and ensure consistent response format handling.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def _create_default_classification_response(self, response_text: str) -> ParsedLLMResponse:
        """Extract: Create default classification when parsing fails."""
        parsed = ParsedLLMResponse(raw_response=response_text)
        parsed.pattern = r"def\s+\w+"
        parsed.group_a_name = "Primary Functions"
        parsed.group_b_name = "Secondary Functions" 
        parsed.reasoning = "Default pattern applied due to response format issues"
        parsed.confidence = 0.3
        return parsed
    
    
    def create_pattern_generation_with_classification_prompt(self, sample_functions: List[Dict[str, Any]]) -> str:
        """
        Create prompt that requests both split pattern and group names using Markdown format.
        
        Args:
            sample_functions: List of function dictionaries with 'name' and 'code' keys
            
        Returns:
            Formatted prompt string requesting pattern and classification in Markdown blocks
        """
        # Limit to 10 functions for better context
        limited_functions = sample_functions[:10]
        
        function_list = ""
        for i, func in enumerate(limited_functions, 1):
            function_list += f"{i}. Function: {func['name']}\n   Code: {func['code']}\n\n"
        
        prompt = f"""Divide the following functions into two meaningful groups and name each group:

{function_list}

IMPORTANT CONSTRAINTS:
1. MUST use the exact format below
2. No additional explanations needed
3. Regex pattern should match function definition lines (def lines)

REQUIRED RESPONSE FORMAT:
```classification
pattern: <regex pattern>
group_a_name: <name for group A>
group_b_name: <name for group B>
reasoning: <classification rationale in one sentence>
```

EXAMPLE:
```classification
pattern: def\\s+(get_|fetch_|load_)
group_a_name: Data Retrieval Functions
group_b_name: Other Processing Functions
reasoning: Clear separation between data retrieval and other processing logic
```

IMPORTANT:
- MUST write inside markdown block
- pattern: followed by regex on one line
- group_a_name: followed by group A name on one line  
- group_b_name: followed by group B name on one line
- reasoning: followed by reason on one line
- No greetings or explanations outside the block"""
        
        return prompt
    
    def create_intent_analysis_prompt(self, code: str) -> str:
        """
        Create standardized intent analysis prompt.
        
        Args:
            code: Code to analyze
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""以下のコードの目的と機能を分析してください：

```python
{code}
```

【必須回答形式】:
PURPOSE: <主要な目的を1行で>
FUNCTIONALITY: <具体的な機能を1行で>

【回答例】:
PURPOSE: ユーザー情報をデータベースから取得する
FUNCTIONALITY: IDを受け取りSQL実行してユーザー辞書を返す"""
        
        return prompt
    
    def parse_classification_block(self, response_text: str) -> ParsedLLMResponse:
        """
        Parse LLM response with Markdown classification block format.
        
        Args:
            response_text: Raw LLM response text containing ```classification``` block
            
        Returns:
            ParsedLLMResponse with extracted pattern, group names and reasoning
            
        Raises:
            ValueError: If required pattern is not found in classification block
        """
        parsed = ParsedLLMResponse(raw_response=response_text)
        
        # Delegate: Extract classification block using dedicated method
        return self._parse_classification_content(response_text, parsed)
    
    def _parse_classification_content(self, response_text: str, parsed: ParsedLLMResponse) -> ParsedLLMResponse:
        """Delegate: Handle classification block extraction and parsing."""
        classification_match = re.search(
            r'```classification\s*\n(.*?)\n```', 
            response_text, 
            re.DOTALL | re.IGNORECASE
        )
        
        if not classification_match:
            self.logger.error(f"No classification block found in response: {response_text[:200]}...")
            return self._create_default_classification_response(response_text)
        
        block_content = classification_match.group(1).strip()
        
        # Parse fields within the block
        field_patterns = {
            'pattern': r'pattern:\s*([^\n\r]+)',
            'group_a_name': r'group_a_name:\s*([^\n\r]+)',
            'group_b_name': r'group_b_name:\s*([^\n\r]+)', 
            'reasoning': r'reasoning:\s*([^\n\r]+)'
        }
        
        for field_name, field_pattern in field_patterns.items():
            match = re.search(field_pattern, block_content, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                if field_name == 'pattern':
                    parsed.pattern = value
                elif field_name == 'group_a_name':
                    parsed.group_a_name = value
                elif field_name == 'group_b_name':
                    parsed.group_b_name = value
                elif field_name == 'reasoning':
                    parsed.reasoning = value
        
        # Validate pattern
        if parsed.pattern:
            try:
                re.compile(parsed.pattern)
                parsed.confidence = 0.9
            except re.error as e:
                self.logger.error(f"Invalid regex pattern: {parsed.pattern} - {e}")
                parsed.pattern = None
                parsed.confidence = 0.0
        
        if not parsed.pattern:
            self.logger.error(f"No valid pattern found in classification block: {response_text[:200]}...")
            return self._create_default_classification_response(response_text)
        
        # Set confidence based on completeness
        if parsed.pattern and parsed.group_a_name and parsed.group_b_name and parsed.reasoning:
            parsed.confidence = 0.95
        elif parsed.pattern and parsed.reasoning:
            parsed.confidence = 0.8
        else:
            parsed.confidence = 0.6
        
        return parsed


    def parse_pattern_response(self, response_text: str) -> ParsedLLMResponse:
        """
        Parse LLM response for pattern generation using Markdown block format only.
        
        Args:
            response_text: Raw LLM response text containing ```classification``` block
            
        Returns:
            ParsedLLMResponse with extracted pattern and reasoning
            
        Raises:
            ValueError: If required pattern is not found in classification block
        """
        return self.parse_classification_block(response_text)
    
    def parse_intent_response(self, response_text: str) -> ParsedLLMResponse:
        """
        Parse LLM response for intent analysis.
        
        Args:
            response_text: Raw LLM response text
            
        Returns:
            ParsedLLMResponse with extracted purpose and functionality
        """
        parsed = ParsedLLMResponse(raw_response=response_text)
        
        # Extract PURPOSE
        purpose_match = re.search(r'PURPOSE:\s*([^\n\r]+)', response_text, re.IGNORECASE)
        if purpose_match:
            parsed.purpose = purpose_match.group(1).strip()
        
        # Extract FUNCTIONALITY  
        func_match = re.search(r'FUNCTIONALITY:\s*([^\n\r]+)', response_text, re.IGNORECASE)
        if func_match:
            parsed.functionality = func_match.group(1).strip()
        
        # Fallback: extract from general text
        if not parsed.purpose and not parsed.functionality:
            # Try to find descriptive content
            lines = response_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith(('Sure', 'I can', 'Here', 'The', 'This')):
                    parsed.purpose = line[:100]  # Take first meaningful line
                    break
        
        parsed.confidence = 0.8 if parsed.purpose or parsed.functionality else 0.3
        
        return parsed
    
    def create_robust_analysis_response(self, parsed: ParsedLLMResponse, 
                                      success: bool = True, 
                                      processing_time: float = 0.0) -> AnalysisResponse:
        """
        Create a standardized AnalysisResponse from parsed data.
        
        Args:
            parsed: ParsedLLMResponse with extracted data
            success: Whether the analysis was successful
            processing_time: Time taken for processing
            
        Returns:
            Standardized AnalysisResponse
        """
        if parsed.pattern:
            # Enhanced pattern response with group names
            result = {
                "pattern": parsed.pattern,
                "reasoning": parsed.reasoning or 'No reasoning provided',
                "group_a_name": parsed.group_a_name or 'Group A',
                "group_b_name": parsed.group_b_name or 'Group B'
            }
            reasoning = f"Pattern generated with classification: {parsed.pattern}"
            
            # Legacy format for backward compatibility
            result["purpose"] = f"PATTERN: {parsed.pattern}\nREASONING: {parsed.reasoning or 'No reasoning provided'}"
            
        elif parsed.purpose or parsed.functionality:
            result = {
                "purpose": parsed.purpose or "Unknown purpose",
                "functionality": parsed.functionality or "General functionality"
            }
            reasoning = "Intent analysis completed"
        else:
            result = {"purpose": "Analysis failed"}
            reasoning = "Failed to extract meaningful data from LLM response"
            success = False
        
        return AnalysisResponse(
            success=success,
            result=result,
            confidence=parsed.confidence,
            reasoning=reasoning,
            metadata={
                "analysis_method": "centralized_llm_handler",
                "raw_response_length": len(parsed.raw_response),
                "pattern_extracted": parsed.pattern is not None,
                "purpose_extracted": parsed.purpose is not None,
                "group_names_extracted": parsed.group_a_name is not None and parsed.group_b_name is not None,
                "format_used": "markdown_block"
            },
            processing_time=processing_time
        )