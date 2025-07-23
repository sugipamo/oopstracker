"""Interactive Exploration Service - Extracted exploration functionality."""

import logging
from typing import Dict, Any, List, Optional

from ..models import CodeRecord
from ..intent_tree_fixed_adapter import FixedIntentTreeAdapter


class InteractiveExplorationService:
    """Service for interactive code exploration using Intent Tree."""
    
    def __init__(self, intent_tree_adapter: FixedIntentTreeAdapter):
        """Initialize exploration service.
        
        Args:
            intent_tree_adapter: Intent Tree adapter instance
        """
        self.intent_tree_adapter = intent_tree_adapter
        self.logger = logging.getLogger(__name__)
    
    async def analyze_with_intent_tree(
        self, 
        code_records: List[CodeRecord]
    ) -> Dict[str, Any]:
        """Perform intent tree analysis on code records.
        
        Args:
            code_records: List of code records to analyze
            
        Returns:
            Analysis results dictionary
        """
        if not self.intent_tree_adapter.intent_tree_available:
            return {"available": False, "reason": "intent_tree not available"}
        
        # Add code records to intent_tree database
        added_count = 0
        for record in code_records:
            if await self.intent_tree_adapter.add_code_snippet(record):
                added_count += 1
        
        # Generate regex features for differentiation
        features = await self.intent_tree_adapter.generate_regex_features(code_records)
        
        # Create exploration sessions for unique codes
        sessions = await self._create_exploration_sessions(code_records[:5])
        
        return {
            "available": True,
            "added_snippets": added_count,
            "generated_features": len(features),
            "exploration_sessions": sessions,
            "features": features[:10]  # Return first 10 features for inspection
        }
    
    async def start_exploration_session(self, query_code: str) -> Dict[str, Any]:
        """Start an interactive exploration session for given code.
        
        Args:
            query_code: Code to explore
            
        Returns:
            Session information dictionary
        """
        if not self.intent_tree_adapter.intent_tree_available:
            return {"available": False, "reason": "intent_tree not available"}
        
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
    
    async def process_exploration_answer(
        self, 
        session_id: str, 
        feature_id: str, 
        matches: bool
    ) -> Dict[str, Any]:
        """Process an answer in the exploration session.
        
        Args:
            session_id: Session identifier
            feature_id: Feature identifier
            matches: Whether the feature matches
            
        Returns:
            Processing result dictionary
        """
        if not self.intent_tree_adapter.intent_tree_available:
            return {"available": False, "reason": "intent_tree not available"}
        
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
    
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Get learning statistics about feature effectiveness and usage patterns.
        
        Returns:
            Statistics dictionary
        """
        if not self.intent_tree_adapter.intent_tree_available:
            return {"available": False, "reason": "intent_tree not available"}
        
        return await self.intent_tree_adapter.get_learning_statistics()
    
    async def _create_exploration_sessions(
        self, 
        code_records: List[CodeRecord]
    ) -> List[Dict[str, Any]]:
        """Create exploration sessions for code records.
        
        Args:
            code_records: List of code records
            
        Returns:
            List of session information dictionaries
        """
        sessions = []
        
        for record in code_records:
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
        
        return sessions