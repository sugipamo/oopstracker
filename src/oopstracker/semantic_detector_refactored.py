"""Semantic-aware duplicate detector with refactored architecture."""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .models import CodeRecord
from .detectors.duplicate_analyzer import DuplicateAnalyzer
from .services.interactive_exploration_service import InteractiveExplorationService
from .integrations.intent_tree_integration import IntentTreeIntegration
from .integrations.interactive_explorer import InteractiveExplorer
from .integrations.learning_stats_manager import LearningStatsManager
from .result_aggregator import ResultAggregator
from .semantic_analysis_coordinator import SemanticAnalysisCoordinator


class SemanticAnalysisStatus(Enum):
    """Status of semantic analysis."""
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


@dataclass
class SemanticDuplicateResult:
    """Result of semantic duplicate detection."""
    code_record_1: CodeRecord
    code_record_2: CodeRecord
    semantic_similarity: float
    confidence: float
    analysis_method: str
    reasoning: str
    analysis_time: float
    status: SemanticAnalysisStatus
    metadata: Dict[str, Any]


class SemanticAwareDuplicateDetector:
    """Duplicate detector with semantic analysis capability - refactored version."""
    
    def __init__(self, intent_unified_available: bool = True, enable_intent_tree: bool = True):
        """Initialize semantic-aware detector.
        
        Args:
            intent_unified_available: Whether intent_unified service is available
            enable_intent_tree: Whether to enable intent_tree integration
        """
        self.intent_unified_available = intent_unified_available
        self.enable_intent_tree = enable_intent_tree
        self.logger = logging.getLogger(__name__)
        self._semantic_threshold = 0.7
        
        # Core components
        self.duplicate_analyzer = DuplicateAnalyzer()
        self.result_aggregator = ResultAggregator()
        
        # Intent Tree components (initialized later)
        self.intent_tree_integration: Optional[IntentTreeIntegration] = None
        self.intent_tree_adapter = None
        self.exploration_service: Optional[InteractiveExplorationService] = None
        self.interactive_explorer: Optional[InteractiveExplorer] = None
        self.learning_stats_manager: Optional[LearningStatsManager] = None
        
        # Semantic components (initialized later)
        self.semantic_coordinator: Optional[SemanticAnalysisCoordinator] = None
        self._intent_unified_facade = None
        
    async def initialize(self) -> None:
        """Initialize semantic analysis components."""
        # Initialize Intent Tree if enabled
        if self.enable_intent_tree:
            self.intent_tree_integration = IntentTreeIntegration(True)
            self.intent_tree_adapter = self.intent_tree_integration.intent_tree_adapter
            await self.intent_tree_adapter.initialize()
            
            # Initialize related services
            self.exploration_service = InteractiveExplorationService(self.intent_tree_adapter)
            self.interactive_explorer = InteractiveExplorer(self.intent_tree_adapter)
            self.learning_stats_manager = LearningStatsManager(self.intent_tree_adapter)
            
            # Show initialization status
            await self._show_intent_tree_status()
        
        # Initialize semantic coordinator
        self.semantic_coordinator = SemanticAnalysisCoordinator(self.intent_unified_available)
        await self.semantic_coordinator.initialize()
        
        # Initialize Intent Unified if available
        if self.intent_unified_available:
            self._intent_unified_facade = await self._initialize_intent_unified()
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        # Cleanup intent_tree adapter
        if self.intent_tree_adapter:
            await self.intent_tree_adapter.cleanup()
        
        # Cleanup Intent Unified
        if self._intent_unified_facade:
            await self._cleanup_intent_unified()
    
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
        # Phase 1: Structural duplicate detection
        structural_results = await self.duplicate_analyzer.analyze_structural_duplicates(
            code_records, threshold=0.7, use_fast_mode=True
        )
        
        # Phase 2: Semantic analysis (if enabled and available)
        semantic_results = []
        if enable_semantic and self.semantic_coordinator and self.semantic_coordinator.intent_unified_available:
            semantic_results = await self._analyze_semantic_duplicates(
                code_records=code_records,
                structural_candidates=structural_results.get("high_confidence", []),
                threshold=semantic_threshold,
                max_concurrent=max_concurrent
            )
        
        # Phase 3: Intent tree analysis (if available)
        intent_tree_results = {}
        if self.exploration_service:
            intent_tree_results = await self.exploration_service.analyze_with_intent_tree(code_records)
        
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
    
    async def explore_code_interactively(self, query_code: str) -> Dict[str, Any]:
        """Start an interactive exploration session for given code."""
        if not self.exploration_service:
            return {"available": False, "reason": "exploration service not initialized"}
        
        return await self.exploration_service.start_exploration_session(query_code)
    
    async def answer_exploration_question(self, session_id: str, feature_id: str, matches: bool) -> Dict[str, Any]:
        """Answer a question in the exploration session."""
        if not self.exploration_service:
            return {"available": False, "reason": "exploration service not initialized"}
        
        return await self.exploration_service.process_exploration_answer(session_id, feature_id, matches)
    
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Get learning statistics about feature effectiveness and usage patterns."""
        if not self.exploration_service:
            return {"available": False, "reason": "exploration service not initialized"}
        
        return await self.exploration_service.get_learning_statistics()
    
    async def _analyze_semantic_duplicates(
        self,
        code_records: List[CodeRecord],
        structural_candidates: List[Tuple[CodeRecord, CodeRecord, float]],
        threshold: float,
        max_concurrent: int
    ) -> List[SemanticDuplicateResult]:
        """Analyze semantic duplicates for structural candidates."""
        # Prepare code pairs
        code_pairs = self.duplicate_analyzer.prepare_code_pairs(structural_candidates, max_pairs=20)
        
        if not code_pairs:
            return []
        
        # Perform semantic analysis
        semantic_results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_pair(code1: str, code2: str, candidate: Tuple[CodeRecord, CodeRecord, float]) -> Optional[SemanticDuplicateResult]:
            async with semaphore:
                start_time = asyncio.get_event_loop().time()
                
                result = await self.semantic_coordinator.analyze_semantic_similarity(
                    code1, code2, intent_tree_adapter=self.intent_tree_adapter
                )
                
                analysis_time = asyncio.get_event_loop().time() - start_time
                
                return SemanticDuplicateResult(
                    code_record_1=candidate[0],
                    code_record_2=candidate[1],
                    semantic_similarity=result.get("similarity", 0.0),
                    confidence=result.get("confidence", 0.0),
                    analysis_method=result.get("method", "unknown"),
                    reasoning=result.get("reasoning", ""),
                    analysis_time=analysis_time,
                    status=SemanticAnalysisStatus.SUCCESS,
                    metadata=result.get("details", {})
                )
        
        # Analyze all pairs concurrently
        tasks = [analyze_pair(code1, code2, candidate) for code1, code2, candidate in code_pairs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        for result in results:
            if isinstance(result, SemanticDuplicateResult):
                semantic_results.append(result)
        
        return semantic_results
    
    async def _initialize_intent_unified(self):
        """Initialize Intent Unified facade.
        
        This method handles the initialization internally and returns
        the facade if successful, or None if not available.
        """
        # Implementation depends on how Intent Unified is made available
        # This is a placeholder for the actual implementation
        return None
    
    async def _cleanup_intent_unified(self):
        """Cleanup Intent Unified facade."""
        # Implementation depends on the actual Intent Unified interface
        pass
    
    async def _show_intent_tree_status(self) -> None:
        """Show user-friendly Intent Tree initialization status."""
        if not self.intent_tree_adapter or not self.intent_tree_adapter.intent_tree_available:
            return
        
        snippets_count = 0
        features_count = len(getattr(self.intent_tree_adapter, 'manual_features', []))
        
        if hasattr(self.intent_tree_adapter, 'db_manager') and self.intent_tree_adapter.db_manager:
            snippets = await self.intent_tree_adapter.db_manager.get_all_snippets()
            snippets_count = len(snippets) if snippets else 0
        
        if snippets_count > 0 or features_count > 0:
            print(f"✅ Intent tree initialized with {snippets_count} snippets and {features_count} features")