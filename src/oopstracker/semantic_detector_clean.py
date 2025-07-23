"""Clean semantic-aware duplicate detector with proper separation of concerns."""

import logging
from typing import Dict, List, Optional, Any

from .models import CodeRecord
from .analyzers.structural_analyzer import StructuralDuplicateAnalyzer
from .analyzers.semantic_analyzer import SemanticDuplicateAnalyzer
from .result_aggregator import ResultAggregator
from .ast_simhash_detector import ASTSimHashDetector
from .semantic_analysis_coordinator import SemanticAnalysisCoordinator


class ComponentFactory:
    """Factory for creating detector components."""
    
    @staticmethod
    def create_structural_analyzer(detector: Optional[ASTSimHashDetector] = None) -> StructuralDuplicateAnalyzer:
        """Create structural analyzer with optional detector injection."""
        return StructuralDuplicateAnalyzer(detector or ASTSimHashDetector())
    
    @staticmethod
    def create_semantic_analyzer(facade: Any, coordinator: Any, adapter: Any) -> SemanticDuplicateAnalyzer:
        """Create semantic analyzer with required dependencies."""
        return SemanticDuplicateAnalyzer(
            facade=facade,
            semantic_coordinator=coordinator,
            intent_tree_adapter=adapter
        )
    
    @staticmethod
    def create_result_aggregator() -> ResultAggregator:
        """Create result aggregator."""
        return ResultAggregator()


class SemanticAwareDuplicateDetectorClean:
    """Clean implementation of duplicate detector with clear separation of concerns."""
    
    def __init__(self, components: Dict[str, Any]):
        """Initialize with pre-configured components.
        
        Args:
            components: Dictionary containing:
                - structural_analyzer: Structural analysis component
                - semantic_analyzer: Semantic analysis component  
                - result_aggregator: Result aggregation component
                - intent_tree_adapter: Intent tree adapter (optional)
                - interactive_explorer: Interactive explorer (optional)
                - learning_stats_manager: Learning stats (optional)
        """
        self.logger = logging.getLogger(__name__)
        
        # Required components
        self.structural_analyzer = components['structural_analyzer']
        self.semantic_analyzer = components.get('semantic_analyzer')
        self.result_aggregator = components['result_aggregator']
        
        # Optional components
        self.intent_tree_adapter = components.get('intent_tree_adapter')
        self.interactive_explorer = components.get('interactive_explorer') 
        self.learning_stats_manager = components.get('learning_stats_manager')
        
        self._semantic_threshold = 0.7
        
    async def detect_duplicates(
        self, 
        code_records: List[CodeRecord], 
        enable_semantic: bool = True,
        semantic_threshold: float = 0.7,
        max_concurrent: int = 3
    ) -> Dict[str, Any]:
        """Detect duplicates with optional semantic analysis.
        
        Args:
            code_records: List of code records to analyze
            enable_semantic: Whether to use semantic analysis
            semantic_threshold: Threshold for semantic similarity
            max_concurrent: Maximum concurrent semantic analyses
            
        Returns:
            Comprehensive duplicate detection results
        """
        # Phase 1: Structural analysis
        structural_results = await self.structural_analyzer.analyze(code_records)
        
        # Phase 2: Semantic analysis (if available and enabled)
        semantic_results = []
        if enable_semantic and self.semantic_analyzer:
            semantic_results = await self.semantic_analyzer.analyze(
                code_records=code_records,
                structural_candidates=structural_results.get("high_confidence", []),
                threshold=semantic_threshold,
                max_concurrent=max_concurrent
            )
        
        # Phase 3: Intent tree analysis (if available)
        intent_tree_results = await self._analyze_with_intent_tree(code_records)
        
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
    
    async def _analyze_with_intent_tree(self, code_records: List[CodeRecord]) -> Dict[str, Any]:
        """Analyze using intent tree if available."""
        if not self.intent_tree_adapter:
            return {"available": False}
            
        added_count = 0
        for record in code_records:
            if await self.intent_tree_adapter.add_code_snippet(record):
                added_count += 1
        
        features = await self.intent_tree_adapter.generate_regex_features(code_records)
        
        return {
            "available": True,
            "added_snippets": added_count,
            "generated_features": len(features),
            "features": features[:10]
        }
    
    async def explore_code_interactively(self, query_code: str) -> Dict[str, Any]:
        """Start interactive exploration if available."""
        if not self.interactive_explorer:
            return {"available": False, "reason": "Interactive explorer not configured"}
            
        return await self.interactive_explorer.explore_code(query_code)
    
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Get learning statistics if available."""
        if not self.learning_stats_manager:
            return {"available": False, "reason": "Learning stats not configured"}
            
        return await self.learning_stats_manager.get_statistics()