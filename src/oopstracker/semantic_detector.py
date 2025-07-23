"""Semantic-aware duplicate detector with fallback to structural analysis."""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .models import CodeRecord
from .intent_tree_fixed_adapter import FixedIntentTreeAdapter
from .integrations.intent_tree_integration import IntentTreeIntegration
from .integrations.interactive_explorer import InteractiveExplorer
from .integrations.learning_stats_manager import LearningStatsManager
from .result_aggregator import ResultAggregator
from .semantic_analysis_coordinator import SemanticAnalysisCoordinator

# Refactored components for better separation of concerns
from .analyzers.structural_analyzer import StructuralAnalyzer
from .analyzers.semantic_analyzer import SemanticAnalyzer, SemanticDuplicateResult, SemanticAnalysisStatus
from .analyzers.result_combiner import ResultCombiner


class SemanticAwareDuplicateDetector:
    """Duplicate detector with semantic analysis capability."""
    
    def __init__(self, intent_unified_available: bool = True, enable_intent_tree: bool = True):
        """Initialize semantic-aware detector.
        
        Args:
            intent_unified_available: Whether intent_unified service is available
            enable_intent_tree: Whether to enable intent_tree integration
        """
        self.intent_unified_available = intent_unified_available
        self.logger = logging.getLogger(__name__)
        self._semantic_threshold = 0.7
        
        # Initialize refactored analyzers
        self.structural_analyzer = StructuralAnalyzer()
        
        # Initialize integrations
        self.intent_tree_integration = IntentTreeIntegration(enable_intent_tree)
        self.intent_tree_adapter = self.intent_tree_integration.intent_tree_adapter
        self.interactive_explorer = InteractiveExplorer(self.intent_tree_adapter)
        self.learning_stats_manager = LearningStatsManager(self.intent_tree_adapter)
        
        # Initialize new components
        self.result_aggregator = ResultAggregator()
        self.result_combiner = ResultCombiner()
        self.semantic_coordinator = SemanticAnalysisCoordinator(intent_unified_available)
        
        # Semantic analyzer with coordinator
        self.semantic_analyzer = SemanticAnalyzer(
            self.semantic_coordinator,
            self.intent_tree_adapter,
            semantic_timeout=30.0
        )
        
    async def initialize(self) -> None:
        """Initialize semantic analysis components."""
        # Initialize intent_tree adapter
        await self.intent_tree_adapter.initialize()
        
        # Show user-friendly initialization message (only if available and has data)
        if self.intent_tree_adapter.intent_tree_available:
            try:
                # Get actual snippet and feature counts from database
                snippets_count = 0
                features_count = len(getattr(self.intent_tree_adapter, 'manual_features', []))
                
                if hasattr(self.intent_tree_adapter, 'db_manager') and self.intent_tree_adapter.db_manager:
                    try:
                        snippets = await self.intent_tree_adapter.db_manager.get_all_snippets()
                        snippets_count = len(snippets) if snippets else 0
                    except Exception as e:
                        print(f"Warning: Failed to retrieve snippets from database: {e}")
                        snippets_count = 0
                
                if snippets_count > 0 or features_count > 0:
                    print(f"✅ Intent tree initialized with {snippets_count} snippets and {features_count} features")
            except Exception as e:
                print(f"Warning: Failed to initialize intent tree status display: {e}")
        
        # Initialize semantic coordinator
        await self.semantic_coordinator.initialize()
        
        if self.intent_unified_available:
            try:
                # Dynamic import to avoid hard dependency
                import sys
                import os
                
                # Add intent_unified to Python path
                intent_unified_path = os.path.join(
                    os.path.dirname(__file__), 
                    "../../../intent/intent-unified/src"
                )
                if intent_unified_path not in sys.path:
                    sys.path.insert(0, intent_unified_path)
                
                from intent_unified.core.facade import IntentUnifiedFacade
                
                self._intent_unified_facade = IntentUnifiedFacade()
                await self._intent_unified_facade.__aenter__()
                
                # Semantic analysis initialized successfully
            except Exception as e:
                self.logger.warning(f"Failed to initialize semantic analysis: {e}")
                self.intent_unified_available = False
                self._intent_unified_facade = None
        
        # Always initialize structural detector
        # ASTSimHashDetector doesn't require async initialization
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        # Cleanup intent_tree adapter
        await self.intent_tree_adapter.cleanup()
        
        if self._intent_unified_facade:
            try:
                await self._intent_unified_facade.__aexit__(None, None, None)
            except Exception as e:
                self.logger.error(f"Error during semantic analyzer cleanup: {e}")
        
        # ASTSimHashDetector doesn't require cleanup
    
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
        structural_results = await self.structural_analyzer.detect_duplicates(code_records)
        
        # Phase 2: Semantic analysis (if enabled and available)
        semantic_results = []
        if enable_semantic and self.semantic_coordinator.intent_unified_available:
            semantic_results = await self.semantic_analyzer.analyze_duplicates(
                code_records=code_records,
                structural_candidates=structural_results.get("high_confidence", []),
                threshold=semantic_threshold,
                max_concurrent=max_concurrent
            )
        
        # Phase 3: Intent tree analysis (if available)
        intent_tree_results = await self.semantic_coordinator.analyze_with_intent_tree(
            code_records, self.intent_tree_adapter
        )
        
        # Phase 4: Aggregate results
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
    
    def _normalize_code_indentation(self, code: str) -> str:
        """Normalize code indentation for comparison."""
        if not code:
            return ""
        
        lines = code.split('\n')
        if not lines:
            return code
        
        # Find minimum indentation (excluding empty lines)
        min_indent = float('inf')
        for line in lines:
            stripped = line.lstrip()
            if stripped:  # Non-empty line
                indent = len(line) - len(stripped)
                min_indent = min(min_indent, indent)
        
        if min_indent == float('inf'):
            return code
        
        # Remove minimum indentation from all lines
        normalized_lines = []
        for line in lines:
            if line.strip():  # Non-empty line
                normalized_lines.append(line[min_indent:])
            else:
                normalized_lines.append('')
        
        return '\n'.join(normalized_lines)
    
    def _combine_results(
        self,
        structural_results: Dict[str, Any],
        semantic_results: List[SemanticDuplicateResult],
        code_records: List[CodeRecord]
    ) -> Dict[str, Any]:
        """Combine structural and semantic results."""
        
        # Create comprehensive duplicate groups
        duplicate_groups = []
        
        # Add high-confidence semantic duplicates
        for semantic_result in semantic_results:
            if semantic_result.status == SemanticAnalysisStatus.SUCCESS:
                duplicate_groups.append({
                    "type": "semantic",
                    "records": [semantic_result.code_record_1, semantic_result.code_record_2],
                    "similarity": semantic_result.semantic_similarity,
                    "confidence": semantic_result.confidence,
                    "method": semantic_result.analysis_method,
                    "reasoning": semantic_result.reasoning,
                    "analysis_time": semantic_result.analysis_time
                })
        
        # Add structural duplicates that weren't analyzed semantically
        for structural_duplicate in structural_results.get("high_confidence", []):
            # Check if this pair was already analyzed semantically
            # structural_duplicate is a tuple (CodeRecord, CodeRecord, float)
            already_analyzed = any(
                s.code_record_1 == structural_duplicate[0] and
                s.code_record_2 == structural_duplicate[1]
                for s in semantic_results
            )
            
            if not already_analyzed:
                duplicate_groups.append({
                    "type": "structural_only",
                    "records": [structural_duplicate[0], structural_duplicate[1]],
                    "similarity": structural_duplicate[2] if len(structural_duplicate) > 2 else 0.8,
                    "confidence": 0.7,  # Moderate confidence for structural only
                    "method": "structural_analysis",
                    "reasoning": "Structural similarity detected, semantic analysis not performed",
                    "analysis_time": 0.0
                })
        
        return {
            "duplicate_groups": duplicate_groups,
            "total_groups": len(duplicate_groups),
            "semantic_analyzed": len(semantic_results),
            "structural_only": len(structural_results.get("high_confidence", [])) - len(semantic_results)
        }
    
    
    async def quick_semantic_check(self, code1: str, code2: str, language: str = "python") -> Dict[str, Any]:
        """Quick semantic similarity check for two code fragments."""
        return await self.semantic_coordinator.analyze_semantic_similarity(
            code1, code2, language, self.intent_tree_adapter
        )
    
    
    async def _analyze_with_intent_tree(self, code_records: List[CodeRecord]) -> Dict[str, Any]:
        """Analyze code records using intent_tree for akinator-style exploration."""
        if not self.intent_tree_adapter.intent_tree_available:
            return {"available": False, "reason": "intent_tree not available"}
        
        try:
            # Add code records to intent_tree database
            added_count = 0
            for record in code_records:
                if await self.intent_tree_adapter.add_code_snippet(record):
                    added_count += 1
            
            # Generate regex features for differentiation
            features = await self.intent_tree_adapter.generate_regex_features(code_records)
            
            # Create exploration sessions for unique codes
            sessions = []
            for record in code_records[:5]:  # Limit to first 5 for demo
                if record.code_content:
                    session_id = await self.intent_tree_adapter.create_exploration_session(
                        record.code_content
                    )
                    if session_id:
                        sessions.append({
                            "session_id": session_id,
                            "code_hash": record.code_hash,
                            "function_name": record.function_name
                        })
            
            return {
                "available": True,
                "added_snippets": added_count,
                "generated_features": len(features),
                "exploration_sessions": sessions,
                "features": features[:10]  # Return first 10 features for inspection
            }
            
        except Exception as e:
            self.logger.error(f"Intent tree analysis failed: {e}")
            return {"available": False, "error": str(e)}
    
    async def explore_code_interactively(self, query_code: str) -> Dict[str, Any]:
        """Start an interactive exploration session for given code."""
        if not self.intent_tree_adapter.intent_tree_available:
            return {"available": False, "reason": "intent_tree not available"}
        
        try:
            session_id = await self.intent_tree_adapter.create_exploration_session(query_code)
            if not session_id:
                return {"available": False, "reason": "Failed to create session"}
            
            question = await self.intent_tree_adapter.get_next_question(session_id)
            
            return {
                "available": True,
                "session_id": session_id,
                "question": question,
                "status": "active"
            }
            
        except Exception as e:
            self.logger.error(f"Interactive exploration failed: {e}")
            return {"available": False, "error": str(e)}
    
    async def answer_exploration_question(self, session_id: str, feature_id: str, matches: bool) -> Dict[str, Any]:
        """Answer a question in the exploration session."""
        if not self.intent_tree_adapter.intent_tree_available:
            return {"available": False, "reason": "intent_tree not available"}
        
        try:
            result = await self.intent_tree_adapter.process_answer(session_id, feature_id, matches)
            if not result:
                return {"available": False, "reason": "Failed to process answer"}
            
            if result["status"] == "completed":
                final_result = await self.intent_tree_adapter.get_exploration_result(session_id)
                return {
                    "available": True,
                    "status": "completed",
                    "result": final_result
                }
            else:
                next_question = await self.intent_tree_adapter.get_next_question(session_id)
                return {
                    "available": True,
                    "status": "active",
                    "question": next_question,
                    "candidates": result["candidates"]
                }
                
        except Exception as e:
            self.logger.error(f"Answer processing failed: {e}")
            return {"available": False, "error": str(e)}
    
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Get learning statistics about feature effectiveness and usage patterns."""
        if not self.intent_tree_adapter.intent_tree_available:
            return {"available": False, "reason": "intent_tree not available"}
            
        try:
            return await self.intent_tree_adapter.get_learning_statistics()
        except Exception as e:
            self.logger.error(f"Failed to get learning statistics: {e}")
            return {"available": False, "error": str(e)}
    
    async def optimize_features_from_history(self) -> Dict[str, Any]:
        """Optimize features based on historical usage patterns."""
        if not self.intent_tree_adapter.intent_tree_available:
            return {"available": False, "reason": "intent_tree not available"}
            
        try:
            return await self.intent_tree_adapter.optimize_features_from_history()
        except Exception as e:
            self.logger.error(f"Failed to optimize features: {e}")
            return {"available": False, "error": str(e)}