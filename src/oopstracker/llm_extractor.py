"""
LLM-based extraction and rule generation utilities.
Extracted from ai_analysis_coordinator.py to improve separation of concerns.
"""

import logging
import re
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime

from .ai_analysis_models import ClassificationRule


class LLMExtractor:
    """Handles LLM-based extraction and rule generation."""
    
    def __init__(self, llm_provider):
        self.logger = logging.getLogger(__name__)
        self._llm_provider = llm_provider
    
    async def extract_classification(self, response_text: str, categories: List[str]) -> Tuple[Optional[str], float, str]:
        """
        Use LLM self-reflection to extract classification from unstructured response.
        
        This is more robust than regex patterns because:
        - Language-agnostic
        - Handles creative expressions  
        - Self-correcting
        - Easier to maintain
        
        Args:
            response_text: Original LLM response
            categories: Available categories
            
        Returns:
            Tuple of (category, confidence, reasoning) or (None, 0.0, error_msg)
        """
        
        extraction_prompt = f"""The following is an AI response about function classification:

"{response_text}"

Please extract the classification information from this response and format it exactly as shown:

Available categories: {', '.join(categories)}

REQUIRED OUTPUT FORMAT:
category: [one of: {', '.join(categories)}]
confidence: [0.0-1.0]
reasoning: [brief explanation]

If the response doesn't clearly indicate a category, respond with:
category: unknown
confidence: 0.0
reasoning: No clear classification found

EXTRACT NOW:"""
        
        try:
            # Use the LLM to parse its own response
            extract_response = await self._llm_provider.generate(extraction_prompt)
            extract_text = extract_response.content if hasattr(extract_response, 'content') else str(extract_response)
            
            # Parse the structured extraction (simpler regex - just for structured output)
            category_match = re.search(r'category:\s*([^\n\r]+)', extract_text, re.IGNORECASE)
            confidence_match = re.search(r'confidence:\s*([^\n\r]+)', extract_text, re.IGNORECASE)
            reasoning_match = re.search(r'reasoning:\s*([^\n\r]+)', extract_text, re.IGNORECASE)
            
            if category_match:
                category = category_match.group(1).strip().lower()
                confidence = float(confidence_match.group(1).strip()) if confidence_match else 0.4
                reasoning = reasoning_match.group(1).strip() if reasoning_match else "Self-extracted from response"
                
                # Validate category
                if category in [c.lower() for c in categories]:
                    return category, confidence * 0.8, f"Self-reflection: {reasoning}"  # Slight confidence penalty for indirection
                else:
                    return None, 0.0, f"Invalid category from self-extraction: {category}"
            else:
                return None, 0.0, "Self-extraction failed to find category"
                
        except Exception as e:
            self.logger.warning(f"LLM self-extraction failed: {e}")
            return None, 0.0, f"Self-extraction error: {str(e)}"
    
    async def extract_intent(self, response_text: str) -> Tuple[Optional[str], Optional[str], float]:
        """
        Use LLM self-reflection to extract intent information from unstructured response.
        
        Args:
            response_text: Original LLM response about code intent
            
        Returns:
            Tuple of (purpose, functionality, confidence)
        """
        
        extraction_prompt = f"""The following is an AI response about code analysis:

"{response_text}"

Please extract the key information and format it exactly as shown:

REQUIRED OUTPUT FORMAT:
purpose: [main purpose in 1-2 sentences]
functionality: [specific functionality description]
confidence: [0.0-1.0]

If no clear intent is described, respond with:
purpose: Unknown function purpose
functionality: General functionality
confidence: 0.3

EXTRACT NOW:"""
        
        try:
            extract_response = await self._llm_provider.generate(extraction_prompt)
            extract_text = extract_response.content if hasattr(extract_response, 'content') else str(extract_response)
            
            purpose_match = re.search(r'purpose:\s*([^\n\r]+)', extract_text, re.IGNORECASE)
            functionality_match = re.search(r'functionality:\s*([^\n\r]+)', extract_text, re.IGNORECASE)
            confidence_match = re.search(r'confidence:\s*([^\n\r]+)', extract_text, re.IGNORECASE)
            
            if purpose_match:
                purpose = purpose_match.group(1).strip()
                functionality = functionality_match.group(1).strip() if functionality_match else "General functionality"
                confidence = float(confidence_match.group(1).strip()) if confidence_match else 0.5
                
                return purpose, functionality, confidence * 0.8  # Slight penalty for indirection
            else:
                return None, None, 0.3
                
        except Exception as e:
            self.logger.warning(f"Intent self-extraction failed: {e}")
            return None, None, 0.3
    
    async def generate_classification_rule(self, code: str, categories: List[str]) -> Optional[ClassificationRule]:
        """
        Generate a new classification rule using LLM.
        
        Returns:
            New ClassificationRule or None if generation failed
        """
        
        # Use the LLMPromptHandler for consistent prompt generation
        from .llm_prompt_handler import LLMPromptHandler
        
        # Create a mock function for the prompt handler
        mock_functions = [{'name': 'unknown_function', 'code': code}]
        
        prompt_handler = LLMPromptHandler()
        prompt = prompt_handler.create_pattern_generation_with_classification_prompt(mock_functions)
        
        # Modify the prompt to focus on single function classification
        # Choose appropriate example based on available categories
        if 'data_processing' in categories:
            example_category = 'data_processing'
            example_pattern = 'def\\s+(process|transform|parse)_\\w+_data'
            example_reasoning = 'Transforms and validates input data structures'
        elif 'utility' in categories:
            example_category = 'utility'
            example_pattern = 'def\\s+\\w+_helper|def\\s+get_\\w+'
            example_reasoning = 'Helper function for common operations'
        else:
            example_category = categories[0]
            example_pattern = 'def\\s+\\w+'
            example_reasoning = 'General function pattern'
            
        classification_prompt = f"""Function:
```python
{code}
```

Categories: {', '.join(categories)}

Example classification format:
```classification
pattern: {example_pattern}
group_a_name: {example_category}
reasoning: {example_reasoning}
```

Based on the function above and available categories, provide a complete classification in the EXACT same format:"""
        
        try:
            # Generate rule using LLM
            llm_response = await self._llm_provider.generate(classification_prompt)
            response_text = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
            
            # Parse the response using the prompt handler
            parsed = prompt_handler.parse_classification_block(response_text)
            
            if parsed.pattern and parsed.group_a_name:
                # Validate the generated pattern
                try:
                    re.compile(parsed.pattern)
                    
                    # Determine the category (use group_a_name as the category)
                    category = parsed.group_a_name.lower()
                    if category not in [c.lower() for c in categories]:
                        # Try to map to a valid category
                        category = self._map_to_valid_category(category, categories)
                    
                    if category:
                        return ClassificationRule(
                            pattern=parsed.pattern,
                            category=category,
                            reasoning=parsed.reasoning or "LLM-generated classification rule",
                            created_at=datetime.now()
                        )
                        
                except re.error as e:
                    self.logger.warning(f"Generated invalid regex pattern: {parsed.pattern} - {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to generate classification rule: {e}")
        
        return None
    
    def _map_to_valid_category(self, suggested_category: str, valid_categories: List[str]) -> Optional[str]:
        """Map a suggested category to a valid one."""
        suggested_lower = suggested_category.lower()
        
        # Direct mapping
        category_mappings = {
            'data_retrieval': 'getter',
            'data_access': 'getter', 
            'accessor': 'getter',
            'retrieve': 'getter',
            'fetch': 'getter',
            'load': 'getter',
            
            'data_modification': 'setter',
            'data_update': 'setter',
            'mutator': 'setter',
            'update': 'setter',
            'save': 'setter',
            'store': 'setter',
            
            'initialization': 'constructor',
            'setup': 'constructor',
            'init': 'constructor',
            
            'testing': 'test',
            'test_function': 'test',
            'unit_test': 'test',
            
            'helper': 'utility',
            'util': 'utility',
            'misc': 'utility',
            'general': 'utility',
            
            'api': 'web_api',
            'endpoint': 'web_api',
            'route': 'web_api',
            'handler': 'web_api',
            
            'transform': 'data_processing',
            'parse': 'data_processing',
            'convert': 'data_processing',
            'process': 'data_processing',
            
            'business': 'business_logic',
            'logic': 'business_logic',
            'calculation': 'business_logic',
            'validation': 'business_logic',
        }
        
        # Look for mapped category
        for key, mapped in category_mappings.items():
            if key in suggested_lower and mapped in [c.lower() for c in valid_categories]:
                return mapped
        
        # Fuzzy matching
        for valid_cat in valid_categories:
            if valid_cat.lower() in suggested_lower or suggested_lower in valid_cat.lower():
                return valid_cat.lower()
        
        return None