"""Refactored semantic-aware duplicate detector using dependency injection and modular design."""

import logging
from typing import Dict, List, Optional, Any, Protocol

from .models import CodeRecord
from .ast_simhash_detector import ASTSimHashDetector
from .semantic_analysis_module import (
    SemanticAnalysisModule, 
    SemanticAnalyzerProtocol,
    SemanticDuplicateResult
)
from .interactive_exploration_module import (
    InteractiveExplorationModule,
    IntentTreeAdapterProtocol
)
from .result_combination_module import ResultCombinationModule
from .result_aggregator import ResultAggregator


class SemanticAwareDuplicateDetectorV2:
    """Refactored duplicate detector with clean separation of concerns."""
    
    def __init__(
        self,
        semantic_analyzer: Optional[SemanticAnalyzerProtocol] = None,
        intent_tree_adapter: Optional[IntentTreeAdapterProtocol] = None,
        enable_semantic: bool = True,
        enable_intent_tree: bool = True
    ):
        """Initialize semantic-aware detector with dependency injection.
        
        Args:
            semantic_analyzer: Implementation of semantic analyzer (injected)
            intent_tree_adapter: Implementation of intent tree adapter (injected)
            enable_semantic: Whether to enable semantic analysis
            enable_intent_tree: Whether to enable intent tree integration
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize modules with injected dependencies
        self.semantic_module = SemanticAnalysisModule(
            semantic_analyzer=semantic_analyzer if enable_semantic else None
        )
        
        self.exploration_module = InteractiveExplorationModule(
            intent_tree_adapter=intent_tree_adapter if enable_intent_tree else None
        )
        
        # Initialize other components
        self.structural_detector = ASTSimHashDetector()
        self.result_combiner = ResultCombinationModule()
        self.result_aggregator = ResultAggregator()
        
        # Status flags
        self.semantic_enabled = enable_semantic and self.semantic_module.is_available
        self.intent_tree_enabled = enable_intent_tree and self.exploration_module.is_available
        
        self.logger.info(
            f"SemanticAwareDuplicateDetectorV2 initialized - "
            f"Semantic: {self.semantic_enabled}, IntentTree: {self.intent_tree_enabled}"
        )
    
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
        # Phase 1: Structural duplicate detection (always run)
        structural_results = await self._detect_structural_duplicates(code_records)
        
        # Phase 2: Semantic analysis (if enabled and available)
        semantic_results = []
        if enable_semantic and self.semantic_enabled:
            semantic_results = await self.semantic_module.analyze_semantic_duplicates(
                code_records=code_records,
                structural_candidates=structural_results.get("high_confidence", []),
                threshold=semantic_threshold,
                max_concurrent=max_concurrent
            )
        
        # Phase 3: Intent tree analysis (if available)
        intent_tree_results = {}
        if self.intent_tree_enabled:
            intent_tree_results = await self.exploration_module.analyze_with_intent_tree(
                code_records
            )
        
        # Phase 4: Combine all results
        combined_results = self.result_combiner.combine_results(
            structural_results, semantic_results, code_records
        )
        
        # Phase 5: Generate final analysis
        analysis_result = self.result_aggregator.aggregate_results(
            structural_results, semantic_results, len(code_records)
        )
        
        return {
            "structural_duplicates": structural_results,
            "semantic_duplicates": semantic_results,
            "combined_analysis": combined_results,
            "intent_tree_analysis": intent_tree_results,
            "summary": analysis_result.summary,
            "recommendation": analysis_result.recommendation,
            "metadata": {
                "semantic_enabled": self.semantic_enabled,
                "intent_tree_enabled": self.intent_tree_enabled,
                "total_records": len(code_records)
            }
        }
    
    async def _detect_structural_duplicates(
        self, 
        code_records: List[CodeRecord]
    ) -> Dict[str, Any]:
        """Detect duplicates using structural analysis.
        
        Args:
            code_records: List of code records to analyze
            
        Returns:
            Structural analysis results
        """
        try:
            # Register code records with structural detector
            for record in code_records:
                if record.code_content and record.function_name:
                    self.structural_detector.register_code(
                        record.code_content, 
                        record.function_name, 
                        record.file_path
                    )
            
            # Find duplicates
            duplicates = self.structural_detector.find_duplicates()
            
            # Get similarity details for all registered codes
            all_similarities = self.structural_detector.get_all_similarities()
            
            # Categorize duplicates by confidence
            high_confidence = []
            medium_confidence = []
            
            for dup_group in duplicates:
                if len(dup_group) >= 2:
                    # Create pairs from duplicate group
                    for i in range(len(dup_group)):
                        for j in range(i + 1, len(dup_group)):
                            code1 = next((r for r in code_records if r.function_name == dup_group[i]), None)
                            code2 = next((r for r in code_records if r.function_name == dup_group[j]), None)
                            
                            if code1 and code2:
                                # Get similarity score
                                similarity = all_similarities.get(
                                    (dup_group[i], dup_group[j]), 
                                    all_similarities.get((dup_group[j], dup_group[i]), 0.8)
                                )
                                
                                if similarity >= 0.85:
                                    high_confidence.append((code1, code2, similarity))
                                else:
                                    medium_confidence.append((code1, code2, similarity))
            
            return {
                "duplicate_groups": duplicates,
                "high_confidence": high_confidence,
                "medium_confidence": medium_confidence,
                "all_similarities": all_similarities
            }
            
        except Exception as e:
            self.logger.error(f"Structural duplicate detection failed: {e}")
            return {
                "duplicate_groups": [],
                "high_confidence": [],
                "medium_confidence": [],
                "all_similarities": {},
                "error": str(e)
            }
    
    async def quick_semantic_check(
        self, code1: str, code2: str, language: str = "python"
    ) -> Dict[str, Any]:
        """Quick semantic similarity check for two code fragments.
        
        Args:
            code1: First code fragment
            code2: Second code fragment
            language: Programming language
            
        Returns:
            Similarity analysis result
        """
        return await self.semantic_module.quick_semantic_check(code1, code2, language)
    
    async def explore_code_interactively(self, query_code: str) -> Dict[str, Any]:
        """Start an interactive exploration session for given code.
        
        Args:
            query_code: Code to explore
            
        Returns:
            Exploration session information
        """
        return await self.exploration_module.explore_code_interactively(query_code)
    
    async def answer_exploration_question(
        self, session_id: str, feature_id: str, matches: bool
    ) -> Dict[str, Any]:
        """Answer a question in the exploration session.
        
        Args:
            session_id: Session identifier
            feature_id: Feature identifier for the question
            matches: Whether the feature matches
            
        Returns:
            Next question or final result
        """
        return await self.exploration_module.answer_exploration_question(
            session_id, feature_id, matches
        )
    
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Get learning statistics about feature effectiveness and usage patterns.
        
        Returns:
            Learning statistics
        """
        return await self.exploration_module.get_learning_statistics()