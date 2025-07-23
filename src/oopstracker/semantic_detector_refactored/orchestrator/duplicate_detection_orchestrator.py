"""Orchestrator for duplicate detection workflow."""

import logging
from typing import Dict, List, Any, Optional

from ...models import CodeRecord
from ...result_aggregator import ResultAggregator
from ..core.structural_detector_service import StructuralDetectorService
from ..core.semantic_detector_service import SemanticDetectorService
from ..integrations.intent_tree_service import IntentTreeService


class DuplicateDetectionOrchestrator:
    """Orchestrates the entire duplicate detection workflow.
    
    This class coordinates between different detection services and
    manages the overall workflow of duplicate detection.
    """
    
    def __init__(
        self,
        intent_unified_available: bool = True,
        enable_intent_tree: bool = True
    ):
        """Initialize the orchestrator with detection services.
        
        Args:
            intent_unified_available: Whether intent_unified service is available
            enable_intent_tree: Whether to enable intent tree integration
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize services
        self.structural_service = StructuralDetectorService()
        self.semantic_service = SemanticDetectorService(intent_unified_available)
        self.intent_tree_service = IntentTreeService(enable_intent_tree)
        
        # Initialize result aggregator
        self.result_aggregator = ResultAggregator()
        
        self.intent_unified_available = intent_unified_available
        self.enable_intent_tree = enable_intent_tree
    
    async def initialize(self) -> None:
        """Initialize all services."""
        self.logger.info("Initializing duplicate detection orchestrator")
        
        # Initialize services in parallel where possible
        await self.semantic_service.initialize()
        await self.intent_tree_service.initialize()
    
    async def cleanup(self) -> None:
        """Cleanup all services."""
        self.logger.info("Cleaning up duplicate detection orchestrator")
        
        await self.semantic_service.cleanup()
        await self.intent_tree_service.cleanup()
    
    async def detect_duplicates(
        self,
        code_records: List[CodeRecord],
        enable_semantic: bool = True,
        semantic_threshold: float = 0.7,
        structural_threshold: float = 0.7,
        max_concurrent: int = 3
    ) -> Dict[str, Any]:
        """Detect duplicates using all available methods.
        
        This is the main entry point for duplicate detection.
        
        Args:
            code_records: List of code records to analyze
            enable_semantic: Whether to use semantic analysis
            semantic_threshold: Threshold for semantic similarity
            structural_threshold: Threshold for structural similarity
            max_concurrent: Maximum concurrent semantic analyses
            
        Returns:
            Comprehensive duplicate detection results
        """
        self.logger.info(f"Starting duplicate detection for {len(code_records)} code records")
        
        # Phase 1: Structural duplicate detection
        structural_results = await self._detect_structural_duplicates(
            code_records, structural_threshold
        )
        
        # Phase 2: Semantic analysis (if enabled)
        semantic_results = []
        if enable_semantic and self.intent_unified_available:
            semantic_results = await self._analyze_semantic_duplicates(
                code_records,
                structural_results,
                semantic_threshold,
                max_concurrent
            )
        
        # Phase 3: Intent tree analysis
        intent_tree_results = {}
        if self.enable_intent_tree:
            intent_tree_results = await self._analyze_with_intent_tree(code_records)
        
        # Phase 4: Aggregate results
        aggregated_result = self._aggregate_results(
            structural_results,
            semantic_results,
            len(code_records)
        )
        
        # Combine all results
        return {
            "structural_duplicates": structural_results,
            "semantic_duplicates": semantic_results,
            "intent_tree_analysis": intent_tree_results,
            "combined_analysis": {
                "summary": aggregated_result.summary,
                "recommendation": aggregated_result.recommendation,
                "duplicate_groups": self._create_duplicate_groups(
                    structural_results,
                    semantic_results
                )
            },
            "summary": aggregated_result.summary
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
            Semantic similarity analysis result
        """
        return await self.semantic_service.quick_check(
            code1, code2, language, self.intent_tree_service.adapter
        )
    
    async def explore_code_interactively(self, query_code: str) -> Dict[str, Any]:
        """Start an interactive exploration session for given code.
        
        Args:
            query_code: Code to explore
            
        Returns:
            Exploration session information
        """
        return await self.intent_tree_service.start_interactive_exploration(query_code)
    
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
        return await self.intent_tree_service.process_exploration_answer(
            session_id, feature_id, matches
        )
    
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Get learning statistics about feature effectiveness.
        
        Returns:
            Learning statistics and insights
        """
        return await self.intent_tree_service.get_learning_statistics()
    
    async def optimize_features_from_history(self) -> Dict[str, Any]:
        """Optimize features based on historical usage patterns.
        
        Returns:
            Optimization results
        """
        return await self.intent_tree_service.optimize_features()
    
    async def _detect_structural_duplicates(
        self,
        code_records: List[CodeRecord],
        threshold: float
    ) -> Dict[str, Any]:
        """Detect structural duplicates.
        
        Args:
            code_records: Code records to analyze
            threshold: Similarity threshold
            
        Returns:
            Structural duplicate detection results
        """
        return await self.structural_service.detect_duplicates(
            code_records,
            threshold=threshold,
            use_fast_mode=True
        )
    
    async def _analyze_semantic_duplicates(
        self,
        code_records: List[CodeRecord],
        structural_results: Dict[str, Any],
        threshold: float,
        max_concurrent: int
    ) -> List[Any]:
        """Analyze semantic duplicates.
        
        Args:
            code_records: All code records
            structural_results: Results from structural analysis
            threshold: Semantic similarity threshold
            max_concurrent: Maximum concurrent analyses
            
        Returns:
            List of semantic duplicate results
        """
        structural_candidates = structural_results.get("high_confidence", [])
        
        return await self.semantic_service.analyze_duplicates(
            code_records,
            structural_candidates,
            threshold=threshold,
            max_concurrent=max_concurrent,
            intent_tree_adapter=self.intent_tree_service.adapter
        )
    
    async def _analyze_with_intent_tree(
        self,
        code_records: List[CodeRecord]
    ) -> Dict[str, Any]:
        """Analyze code records using intent tree.
        
        Args:
            code_records: Code records to analyze
            
        Returns:
            Intent tree analysis results
        """
        return await self.intent_tree_service.analyze_code_records(code_records)
    
    def _aggregate_results(
        self,
        structural_results: Dict[str, Any],
        semantic_results: List[Any],
        total_records: int
    ) -> Any:
        """Aggregate results from different analyses.
        
        Args:
            structural_results: Results from structural analysis
            semantic_results: Results from semantic analysis
            total_records: Total number of code records
            
        Returns:
            Aggregated analysis result
        """
        return self.result_aggregator.aggregate_results(
            structural_results,
            semantic_results,
            total_records
        )
    
    def _create_duplicate_groups(
        self,
        structural_results: Dict[str, Any],
        semantic_results: List[Any]
    ) -> List[Dict[str, Any]]:
        """Create comprehensive duplicate groups.
        
        Args:
            structural_results: Results from structural analysis
            semantic_results: Results from semantic analysis
            
        Returns:
            List of duplicate groups
        """
        duplicate_groups = []
        
        # Add semantic duplicates
        for result in semantic_results:
            if hasattr(result, 'status') and result.status.value == "success":
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
            (r.code_record_1.code_hash, r.code_record_2.code_hash)
            for r in semantic_results
            if hasattr(r, 'code_record_1')
        }
        
        for candidate in structural_results.get("high_confidence", []):
            if len(candidate) >= 2:
                pair_hash = (candidate[0].code_hash, candidate[1].code_hash)
                if pair_hash not in semantic_pairs:
                    duplicate_groups.append({
                        "type": "structural_only",
                        "records": [candidate[0], candidate[1]],
                        "similarity": candidate[2] if len(candidate) > 2 else 0.8,
                        "confidence": 0.7,
                        "method": "structural_analysis",
                        "reasoning": "Structural similarity detected",
                        "analysis_time": 0.0
                    })
        
        return duplicate_groups