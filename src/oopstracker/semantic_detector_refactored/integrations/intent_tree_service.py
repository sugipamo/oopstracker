"""Intent Tree integration service."""

import logging
from typing import Dict, List, Optional, Any

from ...models import CodeRecord
from ...integrations.intent_tree_integration import IntentTreeIntegration
from ...integrations.interactive_explorer import InteractiveExplorer
from ...integrations.learning_stats_manager import LearningStatsManager


class IntentTreeService:
    """Service for managing Intent Tree integration and related features."""
    
    def __init__(self, enable_intent_tree: bool = True):
        """Initialize Intent Tree service.
        
        Args:
            enable_intent_tree: Whether to enable intent tree integration
        """
        self.logger = logging.getLogger(__name__)
        self.enabled = enable_intent_tree
        
        # Initialize integrations
        self.integration = IntentTreeIntegration(enable_intent_tree)
        self.adapter = self.integration.intent_tree_adapter
        self.interactive_explorer = InteractiveExplorer(self.adapter)
        self.stats_manager = LearningStatsManager(self.adapter)
    
    async def initialize(self) -> None:
        """Initialize Intent Tree components."""
        await self.adapter.initialize()
        
        # Show initialization status
        if self.adapter.intent_tree_available:
            await self._display_initialization_status()
    
    async def cleanup(self) -> None:
        """Cleanup Intent Tree resources."""
        await self.adapter.cleanup()
    
    async def analyze_code_records(self, code_records: List[CodeRecord]) -> Dict[str, Any]:
        """Analyze code records using intent tree.
        
        Args:
            code_records: List of code records to analyze
            
        Returns:
            Analysis results including added snippets and generated features
        """
        if not self.adapter.intent_tree_available:
            return {"available": False, "reason": "intent_tree not available"}
        
        try:
            # Add code records to intent tree database
            added_count = 0
            for record in code_records:
                if await self.adapter.add_code_snippet(record):
                    added_count += 1
            
            # Generate regex features for differentiation
            features = await self.adapter.generate_regex_features(code_records)
            
            # Create exploration sessions for unique codes
            sessions = await self._create_exploration_sessions(code_records[:5])
            
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
    
    async def start_interactive_exploration(self, query_code: str) -> Dict[str, Any]:
        """Start an interactive exploration session.
        
        Args:
            query_code: Code to explore
            
        Returns:
            Exploration session information
        """
        return await self.interactive_explorer.start_exploration(query_code)
    
    async def process_exploration_answer(
        self,
        session_id: str,
        feature_id: str,
        matches: bool
    ) -> Dict[str, Any]:
        """Process an answer in the exploration session.
        
        Args:
            session_id: Active session ID
            feature_id: Feature being answered
            matches: Whether the feature matches
            
        Returns:
            Next question or final result
        """
        return await self.interactive_explorer.answer_question(
            session_id, feature_id, matches
        )
    
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Get learning statistics about feature effectiveness.
        
        Returns:
            Learning statistics and insights
        """
        return await self.stats_manager.get_statistics()
    
    async def optimize_features(self) -> Dict[str, Any]:
        """Optimize features based on historical usage.
        
        Returns:
            Optimization results
        """
        return await self.stats_manager.optimize_features()
    
    async def _display_initialization_status(self) -> None:
        """Display initialization status with statistics."""
        try:
            snippets_count = 0
            features_count = len(getattr(self.adapter, 'manual_features', []))
            
            if hasattr(self.adapter, 'db_manager') and self.adapter.db_manager:
                try:
                    snippets = await self.adapter.db_manager.get_all_snippets()
                    snippets_count = len(snippets) if snippets else 0
                except Exception as e:
                    self.logger.warning(f"Failed to retrieve snippets: {e}")
            
            if snippets_count > 0 or features_count > 0:
                print(f"✅ Intent tree initialized with {snippets_count} snippets and {features_count} features")
        except Exception as e:
            self.logger.warning(f"Failed to display initialization status: {e}")
    
    async def _create_exploration_sessions(
        self,
        code_records: List[CodeRecord]
    ) -> List[Dict[str, Any]]:
        """Create exploration sessions for code records.
        
        Args:
            code_records: Code records to create sessions for
            
        Returns:
            List of session information
        """
        sessions = []
        
        for record in code_records:
            if record.code_content:
                session_id = await self.adapter.create_exploration_session(
                    record.code_content
                )
                if session_id:
                    sessions.append({
                        "session_id": session_id,
                        "code_hash": record.code_hash,
                        "function_name": record.function_name
                    })
        
        return sessions