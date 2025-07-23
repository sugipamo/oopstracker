"""Initialization layer for semantic detector components."""

import logging
from typing import Optional

from ..integrations.intent_tree_integration import IntentTreeIntegration
from ..integrations.interactive_explorer import InteractiveExplorer
from ..integrations.learning_stats_manager import LearningStatsManager
from ..result_aggregator import ResultAggregator
from ..analyzers.structural_analyzer import StructuralAnalyzer
from ..analyzers.result_combiner import ResultCombiner
# from ..semantic_analysis_coordinator import SemanticAnalysisCoordinator


class InitializationLayer:
    """Manages initialization of semantic detector components."""
    
    def __init__(self, intent_unified_available: bool = True, enable_intent_tree: bool = True):
        """Initialize the initialization layer.
        
        Args:
            intent_unified_available: Whether intent_unified service is available
            enable_intent_tree: Whether to enable intent_tree integration
        """
        self.intent_unified_available = intent_unified_available
        self.enable_intent_tree = enable_intent_tree
        self.logger = logging.getLogger(__name__)
        
        # Components to be initialized
        self.structural_analyzer: Optional[StructuralAnalyzer] = None
        self.intent_tree_integration: Optional[IntentTreeIntegration] = None
        self.intent_tree_adapter = None
        self.interactive_explorer: Optional[InteractiveExplorer] = None
        self.learning_stats_manager: Optional[LearningStatsManager] = None
        self.result_aggregator: Optional[ResultAggregator] = None
        self.result_combiner: Optional[ResultCombiner] = None
        self.semantic_coordinator = None  # Optional[SemanticAnalysisCoordinator] = None
    
    def initialize_components(self) -> dict:
        """Initialize all components and return them.
        
        Returns:
            Dictionary containing initialized components
        """
        self.logger.info("Initializing semantic detector components...")
        
        # Initialize analyzers
        self.structural_analyzer = StructuralAnalyzer()
        
        # Initialize integrations
        self.intent_tree_integration = IntentTreeIntegration(self.enable_intent_tree)
        self.intent_tree_adapter = self.intent_tree_integration.intent_tree_adapter
        self.interactive_explorer = InteractiveExplorer(self.intent_tree_adapter)
        self.learning_stats_manager = LearningStatsManager(self.intent_tree_adapter)
        
        # Initialize result handling components
        self.result_aggregator = ResultAggregator()
        self.result_combiner = ResultCombiner()
        
        # Initialize semantic coordinator
        # self.semantic_coordinator = SemanticAnalysisCoordinator(self.intent_unified_available)
        
        self.logger.info("Component initialization complete")
        
        return {
            'structural_analyzer': self.structural_analyzer,
            'intent_tree_integration': self.intent_tree_integration,
            'intent_tree_adapter': self.intent_tree_adapter,
            'interactive_explorer': self.interactive_explorer,
            'learning_stats_manager': self.learning_stats_manager,
            'result_aggregator': self.result_aggregator,
            'result_combiner': self.result_combiner,
            'semantic_coordinator': self.semantic_coordinator
        }
    
    async def initialize_async_components(self) -> None:
        """Initialize components that require async setup."""
        if self.semantic_coordinator:
            await self.semantic_coordinator.initialize()
        
        if self.intent_tree_integration:
            # Any async initialization for intent tree
            self.logger.info("Async initialization for intent tree integration complete")
    
    async def cleanup(self) -> None:
        """Clean up initialized components."""
        if self.semantic_coordinator:
            await self.semantic_coordinator.cleanup()
        
        if self.intent_tree_integration:
            # Any cleanup for intent tree
            self.logger.info("Intent tree integration cleanup complete")