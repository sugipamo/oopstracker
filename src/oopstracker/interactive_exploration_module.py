"""Interactive exploration module for code analysis using akinator-style approach."""

import logging
from typing import Dict, List, Any, Optional, Protocol
from .models import CodeRecord


class IntentTreeAdapterProtocol(Protocol):
    """Protocol for intent tree adapters."""
    
    @property
    def intent_tree_available(self) -> bool:
        """Check if intent tree is available."""
        ...
    
    async def add_code_snippet(self, record: CodeRecord) -> bool:
        """Add a code snippet to the intent tree database."""
        ...
    
    async def generate_regex_features(self, code_records: List[CodeRecord]) -> List[Dict[str, Any]]:
        """Generate regex features for differentiation."""
        ...
    
    async def create_exploration_session(self, query_code: str) -> Optional[str]:
        """Create an exploration session for given code."""
        ...
    
    async def get_next_question(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the next question for the session."""
        ...
    
    async def process_answer(self, session_id: str, feature_id: str, matches: bool) -> Optional[Dict[str, Any]]:
        """Process an answer to a question."""
        ...
    
    async def get_exploration_result(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the final result of an exploration session."""
        ...
    
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Get learning statistics."""
        ...


class InteractiveExplorationModule:
    """Module for interactive code exploration using intent tree."""
    
    def __init__(self, intent_tree_adapter: Optional[IntentTreeAdapterProtocol] = None):
        """Initialize interactive exploration module.
        
        Args:
            intent_tree_adapter: Intent tree adapter implementation (dependency injection)
        """
        self.logger = logging.getLogger(__name__)
        self._adapter = intent_tree_adapter
        self.is_available = intent_tree_adapter is not None and intent_tree_adapter.intent_tree_available
    
    async def analyze_with_intent_tree(self, code_records: List[CodeRecord]) -> Dict[str, Any]:
        """Analyze code records using intent_tree for akinator-style exploration.
        
        Args:
            code_records: List of code records to analyze
            
        Returns:
            Analysis results including features and exploration sessions
        """
        if not self.is_available or not self._adapter:
            return {"available": False, "reason": "intent_tree not available"}
        
        try:
            # Add code records to intent_tree database
            added_count = 0
            for record in code_records:
                if await self._adapter.add_code_snippet(record):
                    added_count += 1
            
            # Generate regex features for differentiation
            features = await self._adapter.generate_regex_features(code_records)
            
            # Create exploration sessions for unique codes
            sessions = []
            for record in code_records[:5]:  # Limit to first 5 for demo
                if record.code_content:
                    session_id = await self._adapter.create_exploration_session(
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
        """Start an interactive exploration session for given code.
        
        Args:
            query_code: Code to explore
            
        Returns:
            Exploration session information
        """
        if not self.is_available or not self._adapter:
            return {"available": False, "reason": "intent_tree not available"}
        
        try:
            session_id = await self._adapter.create_exploration_session(query_code)
            if not session_id:
                return {"available": False, "reason": "Failed to create session"}
            
            question = await self._adapter.get_next_question(session_id)
            
            return {
                "available": True,
                "session_id": session_id,
                "question": question,
                "status": "active"
            }
            
        except Exception as e:
            self.logger.error(f"Interactive exploration failed: {e}")
            return {"available": False, "error": str(e)}
    
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
        if not self.is_available or not self._adapter:
            return {"available": False, "reason": "intent_tree not available"}
        
        try:
            result = await self._adapter.process_answer(session_id, feature_id, matches)
            if not result:
                return {"available": False, "reason": "Failed to process answer"}
            
            if result["status"] == "completed":
                final_result = await self._adapter.get_exploration_result(session_id)
                return {
                    "available": True,
                    "status": "completed",
                    "result": final_result
                }
            else:
                next_question = await self._adapter.get_next_question(session_id)
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
        """Get learning statistics about feature effectiveness and usage patterns.
        
        Returns:
            Learning statistics
        """
        if not self.is_available or not self._adapter:
            return {"available": False, "reason": "intent_tree not available"}
            
        try:
            return await self._adapter.get_learning_statistics()
        except Exception as e:
            self.logger.error(f"Failed to get learning statistics: {e}")
            return {"available": False, "error": str(e)}