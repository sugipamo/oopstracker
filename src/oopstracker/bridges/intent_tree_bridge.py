"""Bridge for intent tree functionality."""

from typing import Dict, List, Any, Optional
import logging

from ..models import CodeRecord
from ..integrations.intent_tree_integration import IntentTreeIntegration
from ..integrations.interactive_explorer import InteractiveExplorer
from ..integrations.learning_stats_manager import LearningStatsManager


class IntentTreeBridge:
    """Bridge to intent tree functionality."""
    
    def __init__(self, enable_intent_tree: bool = True):
        """Initialize intent tree bridge."""
        self.integration = IntentTreeIntegration(enable_intent_tree)
        self.adapter = self.integration.intent_tree_adapter
        self.explorer = InteractiveExplorer(self.adapter)
        self.stats_manager = LearningStatsManager(self.adapter)
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self) -> None:
        """Initialize intent tree components."""
        await self.adapter.initialize()
        
        # Display initialization status
        if self.adapter.intent_tree_available:
            await self._display_initialization_status()
    
    async def _display_initialization_status(self) -> None:
        """Display user-friendly initialization message."""
        try:
            snippets_count = 0
            features_count = len(getattr(self.adapter, 'manual_features', []))
            
            if hasattr(self.adapter, 'db_manager') and self.adapter.db_manager:
                try:
                    snippets = await self.adapter.db_manager.get_all_snippets()
                    snippets_count = len(snippets) if snippets else 0
                except Exception as e:
                    print(f"Warning: Failed to retrieve snippets from database: {e}")
            
            if snippets_count > 0 or features_count > 0:
                print(f"✅ Intent tree initialized with {snippets_count} snippets and {features_count} features")
        except Exception as e:
            print(f"Warning: Failed to initialize intent tree status display: {e}")
    
    async def cleanup(self) -> None:
        """Cleanup intent tree resources."""
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
            # Add code records to database
            added_count = 0
            for record in code_records:
                if await self.adapter.add_code_snippet(record):
                    added_count += 1
            
            # Generate features
            features = await self.adapter.generate_regex_features(code_records)
            
            # Create exploration sessions
            sessions = await self._create_exploration_sessions(code_records[:5])
            
            return {
                "available": True,
                "added_snippets": added_count,
                "generated_features": len(features),
                "exploration_sessions": sessions,
                "features": features[:10]
            }
            
        except Exception as e:
            self.logger.error(f"Intent tree analysis failed: {e}")
            return {"available": False, "error": str(e)}
    
    async def _create_exploration_sessions(
        self, 
        code_records: List[CodeRecord]
    ) -> List[Dict[str, Any]]:
        """Create exploration sessions for code records."""
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
    
    async def start_exploration(self, query_code: str) -> Dict[str, Any]:
        """Start an interactive exploration session.
        
        Args:
            query_code: Code to explore
            
        Returns:
            Session information and first question
        """
        if not self.adapter.intent_tree_available:
            return {"available": False, "reason": "intent_tree not available"}
        
        try:
            session_id = await self.adapter.create_exploration_session(query_code)
            if not session_id:
                return {"available": False, "reason": "Failed to create session"}
            
            question = await self.adapter.get_next_question(session_id)
            
            return {
                "available": True,
                "session_id": session_id,
                "question": question,
                "status": "active"
            }
            
        except Exception as e:
            self.logger.error(f"Interactive exploration failed: {e}")
            return {"available": False, "error": str(e)}
    
    async def process_answer(
        self, 
        session_id: str, 
        feature_id: str, 
        matches: bool
    ) -> Dict[str, Any]:
        """Process an answer in exploration session.
        
        Args:
            session_id: Exploration session ID
            feature_id: Feature ID being answered
            matches: Whether the feature matches
            
        Returns:
            Next question or final result
        """
        if not self.adapter.intent_tree_available:
            return {"available": False, "reason": "intent_tree not available"}
        
        try:
            result = await self.adapter.process_answer(session_id, feature_id, matches)
            if not result:
                return {"available": False, "reason": "Failed to process answer"}
            
            if result["status"] == "completed":
                final_result = await self.adapter.get_exploration_result(session_id)
                return {
                    "available": True,
                    "status": "completed",
                    "result": final_result
                }
            else:
                next_question = await self.adapter.get_next_question(session_id)
                return {
                    "available": True,
                    "status": "active",
                    "question": next_question,
                    "candidates": result["candidates"]
                }
                
        except Exception as e:
            self.logger.error(f"Answer processing failed: {e}")
            return {"available": False, "error": str(e)}
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get learning statistics.
        
        Returns:
            Feature effectiveness and usage statistics
        """
        if not self.adapter.intent_tree_available:
            return {"available": False, "reason": "intent_tree not available"}
            
        try:
            return await self.adapter.get_learning_statistics()
        except Exception as e:
            self.logger.error(f"Failed to get learning statistics: {e}")
            return {"available": False, "error": str(e)}
    
    async def optimize_features(self) -> Dict[str, Any]:
        """Optimize features based on usage history.
        
        Returns:
            Optimization results
        """
        if not self.adapter.intent_tree_available:
            return {"available": False, "reason": "intent_tree not available"}
            
        try:
            return await self.adapter.optimize_features_from_history()
        except Exception as e:
            self.logger.error(f"Failed to optimize features: {e}")
            return {"available": False, "error": str(e)}