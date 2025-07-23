"""Adapter implementations for semantic analyzers."""

import logging
from typing import Dict, Any
from .semantic_analysis_module import SemanticAnalyzerProtocol


class IntentUnifiedAdapter:
    """Adapter for intent_unified facade to conform to SemanticAnalyzerProtocol."""
    
    def __init__(self, intent_unified_facade):
        """Initialize adapter with intent_unified facade.
        
        Args:
            intent_unified_facade: Instance of IntentUnifiedFacade
        """
        self._facade = intent_unified_facade
        self.logger = logging.getLogger(__name__)
    
    async def analyze_semantic_similarity(
        self, code1: str, code2: str, language: str = "python"
    ) -> Dict[str, Any]:
        """Analyze semantic similarity between two code snippets.
        
        Args:
            code1: First code snippet
            code2: Second code snippet
            language: Programming language
            
        Returns:
            Analysis result dictionary
        """
        result = await self._facade.analyze_semantic_similarity(
            code1, code2, language=language
        )
        return result