"""
Simple LLM analyzer using easy-to-parse formats for low-performance models.
"""

import re
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SimpleAnalysisResult:
    """Result from simple LLM analysis."""
    similarity: float
    confidence: float
    reasoning: str
    method: str = "simple_llm"


class SimpleLLMAnalyzer:
    """Analyzer using simple prompts that work well with low-performance LLMs."""
    
    def __init__(self):
        self.strategies = [
            self._percentage_strategy,
            self._yes_no_strategy,
            self._multiple_choice_strategy,
            self._scale_strategy,
        ]
    
    async def analyze(self, code1: str, code2: str, llm_provider) -> Optional[SimpleAnalysisResult]:
        """Try multiple simple strategies to get similarity score."""
        
        # Try each strategy until one succeeds
        for strategy in self.strategies:
            try:
                result = await strategy(code1, code2, llm_provider)
                if result:
                    logger.debug(f"Strategy {strategy.__name__} succeeded")
                    return result
            except Exception as e:
                logger.debug(f"Strategy {strategy.__name__} failed: {e}")
                continue
        
        return None
    
    async def _percentage_strategy(self, code1: str, code2: str, llm_provider) -> Optional[SimpleAnalysisResult]:
        """Ask for a simple percentage."""
        prompt = f"""What percentage similar are these two functions? Answer with just a number and %.

Function 1: {code1[:100]}
Function 2: {code2[:100]}

Similarity: ____%"""
        
        response = await llm_provider.generate(prompt, 
                                             system_prompt="Give percentage only")
        
        # Extract percentage
        match = re.search(r'(\d+)\s*%', response.content)
        if match:
            similarity = float(match.group(1)) / 100
            return SimpleAnalysisResult(
                similarity=similarity,
                confidence=0.85,  # High confidence for this simple format
                reasoning=f"Functions are {int(similarity*100)}% similar",
                method="percentage"
            )
        
        return None
    
    async def _yes_no_strategy(self, code1: str, code2: str, llm_provider) -> Optional[SimpleAnalysisResult]:
        """Simple YES/NO question."""
        prompt = f"""Are these two functions doing the same thing?

{code1[:150]}

{code2[:150]}

Answer: YES or NO"""
        
        response = await llm_provider.generate(prompt,
                                             system_prompt="Answer YES or NO only")
        
        text = response.content.upper()
        if "YES" in text:
            return SimpleAnalysisResult(
                similarity=0.85,
                confidence=0.8,
                reasoning="Functions perform the same operation",
                method="yes_no"
            )
        elif "NO" in text:
            return SimpleAnalysisResult(
                similarity=0.15,
                confidence=0.8,
                reasoning="Functions perform different operations",
                method="yes_no"
            )
        
        return None
    
    async def _multiple_choice_strategy(self, code1: str, code2: str, llm_provider) -> Optional[SimpleAnalysisResult]:
        """Multiple choice format."""
        prompt = f"""How similar are these functions?

{code1[:100]}
{code2[:100]}

A) Almost identical
B) Similar purpose
C) Different

Choose A, B, or C:"""
        
        response = await llm_provider.generate(prompt,
                                             system_prompt="Choose A, B, or C")
        
        text = response.content.upper()
        
        # Look for A, B, or C
        for choice, (sim, reason) in {
            'A': (0.9, "Functions are almost identical"),
            'B': (0.6, "Functions have similar purpose"),
            'C': (0.2, "Functions are different")
        }.items():
            if choice in text:
                return SimpleAnalysisResult(
                    similarity=sim,
                    confidence=0.8,
                    reasoning=reason,
                    method="multiple_choice"
                )
        
        return None
    
    async def _scale_strategy(self, code1: str, code2: str, llm_provider) -> Optional[SimpleAnalysisResult]:
        """Simple 1-10 scale."""
        prompt = f"""Rate similarity from 1 to 10:

{code1[:100]}
vs
{code2[:100]}

Rating (1-10):"""
        
        response = await llm_provider.generate(prompt,
                                             system_prompt="Give a number from 1 to 10")
        
        # Extract number
        match = re.search(r'(\d+)', response.content)
        if match:
            rating = int(match.group(1))
            if 1 <= rating <= 10:
                similarity = rating / 10
                return SimpleAnalysisResult(
                    similarity=similarity,
                    confidence=0.75,
                    reasoning=f"Similarity rating: {rating}/10",
                    method="scale"
                )
        
        return None
    
    def combine_with_structural(self, llm_result: SimpleAnalysisResult, 
                              structural_similarity: float) -> Dict[str, Any]:
        """Combine simple LLM result with structural analysis."""
        # Weight based on confidence
        llm_weight = llm_result.confidence
        struct_weight = 1 - llm_weight
        
        combined_similarity = (
            llm_result.similarity * llm_weight + 
            structural_similarity * struct_weight
        )
        
        return {
            "similarity": combined_similarity,
            "confidence": llm_result.confidence,
            "reasoning": llm_result.reasoning,
            "method": "hybrid",
            "details": {
                "llm_similarity": llm_result.similarity,
                "structural_similarity": structural_similarity,
                "llm_method": llm_result.method
            }
        }