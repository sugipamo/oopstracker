"""
LLM Extraction Service - Handles LLM self-reflection for extracting structured information.
"""

import re
import logging
from typing import Tuple, Optional, List


class LLMExtractionService:
    """Service for extracting structured information from LLM responses."""
    
    def __init__(self, llm_provider):
        self.logger = logging.getLogger(__name__)
        self._llm_provider = llm_provider
    
    async def extract_classification(self, response_text: str, categories: List[str]) -> Tuple[Optional[str], float, str]:
        """
        Use LLM self-reflection to extract classification from unstructured response.
        
        Args:
            response_text: Original LLM response about function classification
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
            
            # Parse the structured extraction
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
            self.logger.warning(f"LLM intent extraction failed: {e}")
            return None, None, 0.3