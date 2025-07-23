"""Refactored semantic-aware duplicate detector using bridge pattern."""

import logging
from typing import Dict, List, Optional, Tuple, Any

from .models import CodeRecord
from .result_aggregator import ResultAggregator
from .bridges.structural_bridge import StructuralAnalysisBridge
from .bridges.semantic_bridge import SemanticAnalysisBridge, SemanticDuplicateResult
from .bridges.intent_tree_bridge import IntentTreeBridge


class SemanticAwareDuplicateDetector:
    """Duplicate detector with layered architecture."""
    
    def __init__(
        self, 
        intent_unified_available: bool = True, 
        enable_intent_tree: bool = True
    ):
        """Initialize detector with bridge components.
        
        Args:
            intent_unified_available: Whether intent_unified service is available
            enable_intent_tree: Whether to enable intent_tree integration
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize bridges
        self.structural_bridge = StructuralAnalysisBridge()
        self.semantic_bridge = SemanticAnalysisBridge(intent_unified_available)
        self.intent_tree_bridge = IntentTreeBridge(enable_intent_tree)
        
        # Initialize aggregator
        self.result_aggregator = ResultAggregator()
        
    async def initialize(self) -> None:
        """Initialize all analysis components."""
        await self.intent_tree_bridge.initialize()
        await self.semantic_bridge.initialize()
        
    async def cleanup(self) -> None:
        """Cleanup all resources."""
        await self.intent_tree_bridge.cleanup()
        
    async def detect_duplicates(
        self, 
        code_records: List[CodeRecord], 
        enable_semantic: bool = True,
        semantic_threshold: float = 0.7,
        max_concurrent: int = 3
    ) -> Dict[str, Any]:
        """Detect duplicates using multiple analysis layers.
        
        Args:
            code_records: List of code records to analyze
            enable_semantic: Whether to use semantic analysis
            semantic_threshold: Threshold for semantic similarity
            max_concurrent: Maximum concurrent semantic analyses
            
        Returns:
            Comprehensive duplicate detection results
        """
        # Layer 1: Structural Analysis
        structural_results = await self.structural_bridge.analyze(
            code_records, threshold=0.7
        )
        
        # Layer 2: Semantic Analysis (if enabled)
        semantic_results = []
        if enable_semantic and structural_results.get("high_confidence"):
            semantic_results = await self.semantic_bridge.analyze(
                code_records=code_records,
                structural_candidates=structural_results["high_confidence"],
                threshold=semantic_threshold,
                max_concurrent=max_concurrent,
                intent_tree_adapter=self.intent_tree_bridge.adapter
            )
        
        # Layer 3: Intent Tree Analysis
        intent_tree_results = await self.intent_tree_bridge.analyze_code_records(
            code_records
        )
        
        # Aggregate all results
        analysis_result = self.result_aggregator.aggregate_results(
            structural_results, semantic_results, len(code_records)
        )
        
        return {
            "structural_duplicates": structural_results,
            "semantic_duplicates": semantic_results,
            "combined_analysis": {
                "summary": analysis_result.summary,
                "recommendation": analysis_result.recommendation
            },
            "intent_tree_analysis": intent_tree_results,
            "summary": analysis_result.summary
        }
    
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
            Semantic similarity results
        """
        return await self.semantic_bridge.quick_check(
            code1, code2, language, self.intent_tree_bridge.adapter
        )
    
    async def explore_code_interactively(self, query_code: str) -> Dict[str, Any]:
        """Start an interactive exploration session for given code.
        
        Args:
            query_code: Code to explore
            
        Returns:
            Exploration session information
        """
        return await self.intent_tree_bridge.start_exploration(query_code)
    
    async def answer_exploration_question(
        self, 
        session_id: str, 
        feature_id: str, 
        matches: bool
    ) -> Dict[str, Any]:
        """Answer a question in the exploration session.
        
        Args:
            session_id: Exploration session ID
            feature_id: Feature ID being answered
            matches: Whether the feature matches
            
        Returns:
            Next question or final result
        """
        return await self.intent_tree_bridge.process_answer(
            session_id, feature_id, matches
        )
    
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Get learning statistics about feature effectiveness.
        
        Returns:
            Learning statistics
        """
        return await self.intent_tree_bridge.get_statistics()
    
    async def optimize_features_from_history(self) -> Dict[str, Any]:
        """Optimize features based on historical usage patterns.
        
        Returns:
            Optimization results
        """
        return await self.intent_tree_bridge.optimize_features()
    
    def _combine_results(
        self,
        structural_results: Dict[str, Any],
        semantic_results: List[SemanticDuplicateResult],
        code_records: List[CodeRecord]
    ) -> Dict[str, Any]:
        """Combine structural and semantic results.
        
        This method is kept for backward compatibility.
        New code should use the result_aggregator directly.
        """
        # Create duplicate groups
        duplicate_groups = []
        
        # Add semantic duplicates
        for result in semantic_results:
            if result.status.value == "success":
                duplicate_groups.append({
                    "type": "semantic",
                    "records": [result.code_record_1, result.code_record_2],
                    "similarity": result.semantic_similarity,
                    "confidence": result.confidence,
                    "method": result.analysis_method,
                    "reasoning": result.reasoning,
                    "analysis_time": result.analysis_time
                })
        
        # Add structural-only duplicates
        semantic_pairs = {
            (r.code_record_1, r.code_record_2) for r in semantic_results
        }
        
        for duplicate in structural_results.get("high_confidence", []):
            pair = (duplicate[0], duplicate[1])
            if pair not in semantic_pairs:
                duplicate_groups.append({
                    "type": "structural_only",
                    "records": list(pair),
                    "similarity": duplicate[2] if len(duplicate) > 2 else 0.8,
                    "confidence": 0.7,
                    "method": "structural_analysis",
                    "reasoning": "Structural similarity detected",
                    "analysis_time": 0.0
                })
        
        return {
            "duplicate_groups": duplicate_groups,
            "total_groups": len(duplicate_groups),
            "semantic_analyzed": len(semantic_results),
            "structural_only": len(structural_results.get("high_confidence", [])) - len(semantic_results)
        }