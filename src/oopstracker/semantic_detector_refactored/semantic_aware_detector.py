"""Refactored semantic-aware duplicate detector.

This module provides a clean interface to the refactored duplicate detection system.
It acts as a facade to the orchestrator and maintains API compatibility.
"""

from typing import Dict, List, Any

from ..models import CodeRecord
from .orchestrator.duplicate_detection_orchestrator import DuplicateDetectionOrchestrator


class SemanticAwareDuplicateDetector:
    """Semantic-aware duplicate detector with clean architecture.
    
    This class provides a simplified interface to the duplicate detection
    system while maintaining backward compatibility with the original API.
    """
    
    def __init__(
        self,
        intent_unified_available: bool = True,
        enable_intent_tree: bool = True
    ):
        """Initialize semantic-aware detector.
        
        Args:
            intent_unified_available: Whether intent_unified service is available
            enable_intent_tree: Whether to enable intent_tree integration
        """
        self.orchestrator = DuplicateDetectionOrchestrator(
            intent_unified_available=intent_unified_available,
            enable_intent_tree=enable_intent_tree
        )
        
        # Maintain compatibility attributes
        self.intent_unified_available = intent_unified_available
        self._semantic_threshold = 0.7
    
    async def initialize(self) -> None:
        """Initialize semantic analysis components."""
        await self.orchestrator.initialize()
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self.orchestrator.cleanup()
    
    async def detect_duplicates(
        self,
        code_records: List[CodeRecord],
        enable_semantic: bool = True,
        semantic_threshold: float = 0.7,
        max_concurrent: int = 3
    ) -> Dict[str, Any]:
        """Detect duplicates with semantic analysis.
        
        Args:
            code_records: List of code records to analyze
            enable_semantic: Whether to use semantic analysis
            semantic_threshold: Threshold for semantic similarity
            max_concurrent: Maximum concurrent semantic analyses
            
        Returns:
            Comprehensive duplicate detection results
        """
        return await self.orchestrator.detect_duplicates(
            code_records=code_records,
            enable_semantic=enable_semantic,
            semantic_threshold=semantic_threshold,
            structural_threshold=0.7,
            max_concurrent=max_concurrent
        )
    
    async def quick_semantic_check(
        self,
        code1: str,
        code2: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """Quick semantic similarity check for two code fragments.
        
        Args:
            code1: First code fragment
            code2: Second code fragment
            language: Programming language
            
        Returns:
            Semantic similarity analysis result
        """
        return await self.orchestrator.quick_semantic_check(
            code1, code2, language
        )
    
    async def explore_code_interactively(
        self,
        query_code: str
    ) -> Dict[str, Any]:
        """Start an interactive exploration session for given code.
        
        Args:
            query_code: Code to explore
            
        Returns:
            Exploration session information
        """
        return await self.orchestrator.explore_code_interactively(query_code)
    
    async def answer_exploration_question(
        self,
        session_id: str,
        feature_id: str,
        matches: bool
    ) -> Dict[str, Any]:
        """Answer a question in the exploration session.
        
        Args:
            session_id: Active session ID
            feature_id: Feature being answered
            matches: Whether the feature matches
            
        Returns:
            Next question or final result
        """
        return await self.orchestrator.answer_exploration_question(
            session_id, feature_id, matches
        )
    
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Get learning statistics about feature effectiveness.
        
        Returns:
            Learning statistics and insights
        """
        return await self.orchestrator.get_learning_statistics()
    
    async def optimize_features_from_history(self) -> Dict[str, Any]:
        """Optimize features based on historical usage patterns.
        
        Returns:
            Optimization results
        """
        return await self.orchestrator.optimize_features_from_history()