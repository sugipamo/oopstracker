"""
Similarity analysis component for AI Analysis.
"""
import asyncio
import logging
from typing import Dict, Any

from .interface import AnalysisResponse
from .llm_manager import LLMProviderManager


class SimilarityAnalyzer:
    """Handles code similarity analysis using LLM."""
    
    def __init__(self, llm_manager: LLMProviderManager):
        self.logger = logging.getLogger(__name__)
        self.llm_manager = llm_manager
    
    async def analyze_similarity(self, code1: str, code2: str, **kwargs) -> AnalysisResponse:
        """Analyze similarity between two code snippets."""
        start_time = asyncio.get_event_loop().time()
        
        if not self.llm_manager.available:
            raise RuntimeError("LLM provider is not available")
        
        timeout = kwargs.get('timeout', None)  # Use LLM-Providers default
        language = kwargs.get('language', 'python')
        
        # Use semantic analyzer for similarity
        result = await self.llm_manager.semantic_analyzer.analyze_semantic_similarity(
            code1, code2, 
            language=language,
            timeout=timeout
        )
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        # Extract results
        similarity_score = result.get('similarity', 0.0)
        analysis = result.get('analysis', {})
        
        # Build detailed reasoning
        reasoning_parts = []
        if 'reasoning' in result:
            reasoning_parts.append(result['reasoning'])
        
        if analysis.get('shared_concepts'):
            reasoning_parts.append(f"Shared concepts: {', '.join(analysis['shared_concepts'])}")
        
        if analysis.get('structural_similarity'):
            reasoning_parts.append(f"Structural similarity: {analysis['structural_similarity']:.2f}")
        
        reasoning = " | ".join(reasoning_parts) if reasoning_parts else "Similarity analysis completed"
        
        # Prepare metadata
        metadata = {
            'language': language,
            'model': result.get('model', 'unknown'),
            'analysis_details': analysis,
            'raw_response': result.get('raw_response')
        }
        
        return AnalysisResponse(
            success=True,
            result={
                'similarity': similarity_score,
                'is_similar': similarity_score > 0.7,
                'analysis': analysis
            },
            confidence=result.get('confidence', similarity_score),
            reasoning=reasoning,
            metadata=metadata,
            processing_time=processing_time
        )