"""Interactive code exploration module."""

import logging
from typing import Dict, Any, Optional

from ..intent_tree_fixed_adapter import FixedIntentTreeAdapter


class InteractiveExplorer:
    """Handles interactive code exploration functionality."""
    
    def __init__(self, intent_tree_adapter: FixedIntentTreeAdapter):
        """Initialize interactive explorer.
        
        Args:
            intent_tree_adapter: Intent tree adapter instance
        """
        self.logger = logging.getLogger(__name__)
        self.intent_tree_adapter = intent_tree_adapter
        
    async def explore_code_interactively(self, query_code: str) -> Dict[str, Any]:
        """Start an interactive exploration session for code understanding.
        
        Args:
            query_code: The code to explore
            
        Returns:
            Exploration session information
        """
        if not self.intent_tree_adapter.intent_tree_available:
            return {
                "status": "unavailable",
                "message": "Intent tree is not available for interactive exploration"
            }
            
        # Create exploration session
        session_id = await self.intent_tree_adapter.create_exploration_session(query_code)
        
        if not session_id:
            return {
                "status": "failed",
                "message": "Failed to create exploration session"
            }
            
        # Get first question
        first_question = await self.intent_tree_adapter.get_next_question(session_id)
        
        if not first_question:
            return {
                "status": "failed",
                "message": "No questions available for exploration"
            }
            
        return {
            "status": "active",
            "session_id": session_id,
            "current_question": first_question,
            "message": "Interactive exploration session started"
        }
        
    async def answer_exploration_question(self, session_id: str, feature_id: str, matches: bool) -> Dict[str, Any]:
        """Answer a question in the exploration session.
        
        Args:
            session_id: The exploration session ID
            feature_id: The feature being questioned
            matches: Whether the feature matches the code
            
        Returns:
            Next question or final result
        """
        if not self.intent_tree_adapter.intent_tree_available:
            return {
                "status": "unavailable",
                "message": "Intent tree is not available"
            }
            
        # Process the answer
        result = await self.intent_tree_adapter.process_answer(session_id, feature_id, matches)
        
        if not result:
            return {
                "status": "error",
                "message": "Failed to process answer"
            }
            
        # Check if exploration is complete
        if result.get("complete", False):
            final_result = await self.intent_tree_adapter.get_exploration_result(session_id)
            return {
                "status": "complete",
                "result": final_result,
                "message": "Exploration complete"
            }
            
        # Get next question
        next_question = await self.intent_tree_adapter.get_next_question(session_id)
        
        if not next_question:
            # No more questions, get final result
            final_result = await self.intent_tree_adapter.get_exploration_result(session_id)
            return {
                "status": "complete",
                "result": final_result,
                "message": "Exploration complete"
            }
            
        return {
            "status": "active",
            "session_id": session_id,
            "current_question": next_question,
            "message": "Next question ready"
        }