"""Intent Tree integration module for semantic analysis."""

import logging
from typing import Dict, List, Any, Optional, Tuple

from ..models import CodeRecord
from ..intent_tree_fixed_adapter import FixedIntentTreeAdapter


class IntentTreeIntegration:
    """Handles all Intent Tree related operations."""
    
    def __init__(self, enable_intent_tree: bool = True):
        """Initialize Intent Tree integration.
        
        Args:
            enable_intent_tree: Whether to enable intent tree integration
        """
        self.logger = logging.getLogger(__name__)
        self.intent_tree_adapter = FixedIntentTreeAdapter(enable_intent_tree)
        self.intent_tree_available = enable_intent_tree
        
    async def initialize(self) -> None:
        """Initialize intent tree adapter."""
        await self.intent_tree_adapter.initialize()
        
        if not self.intent_tree_adapter.intent_tree_available:
            self.logger.info("Intent tree not available.")
            return
            
        # Get feature and snippet counts
        features_count = self._get_features_count()
        snippets_count = await self._get_snippets_count()
        
        if snippets_count > 0 or features_count > 0:
            print(f"✅ Intent tree initialized with {snippets_count} snippets and {features_count} features")
                
    async def cleanup(self) -> None:
        """Cleanup intent tree resources."""
        if hasattr(self.intent_tree_adapter, 'cleanup'):
            await self.intent_tree_adapter.cleanup()
            
    def _get_features_count(self) -> int:
        """Get the count of manual features.
        
        Returns:
            Number of manual features
        """
        manual_features = getattr(self.intent_tree_adapter, 'manual_features', None)
        if manual_features is None:
            return 0
        return len(manual_features)
        
    async def _get_snippets_count(self) -> int:
        """Get the count of snippets from database.
        
        Returns:
            Number of snippets in database
        """
        db_manager = getattr(self.intent_tree_adapter, 'db_manager', None)
        if not db_manager:
            self.logger.debug("db_manager not available; skipping snippet count retrieval.")
            return 0
            
        # Check if db_manager has a safe method
        if hasattr(db_manager, 'safe_get_all_snippets'):
            snippets = await db_manager.safe_get_all_snippets()
            return len(snippets) if snippets else 0
            
        # If no safe method exists, we cannot retrieve snippets safely
        self.logger.debug("db_manager does not have safe_get_all_snippets method.")
        return 0
            
    async def analyze_with_intent_tree(self, code_records: List[CodeRecord]) -> Dict[str, Any]:
        """Analyze code records using intent tree.
        
        Args:
            code_records: List of code records to analyze
            
        Returns:
            Analysis results from intent tree
        """
        if not self.intent_tree_available:
            return self._empty_analysis_result()
            
        # Check if adapter has safe feature extraction method
        if not hasattr(self.intent_tree_adapter, 'safe_extract_features'):
            self.logger.warning("Intent tree adapter does not support safe feature extraction")
            return self._empty_analysis_result()
            
        # Extract features for all code records
        all_features = await self._extract_all_features_safe(code_records)
        
        # Find matches based on features
        matches = self._find_feature_matches(all_features)
                            
        return {
            "features": all_features,
            "matches": matches
        }
        
    async def _extract_all_features_safe(self, code_records: List[CodeRecord]) -> Dict[str, Any]:
        """Extract features for all code records using safe method.
        
        Args:
            code_records: List of code records
            
        Returns:
            Dictionary mapping function names to their features
        """
        all_features = {}
        
        for record in code_records:
            # Use safe feature extraction if available
            if hasattr(self.intent_tree_adapter, 'safe_extract_features'):
                features = await self.intent_tree_adapter.safe_extract_features(record.snippet)
                if features:
                    all_features[record.full_name] = features
            else:
                # Skip if safe method not available
                self.logger.debug(f"Skipping feature extraction for {record.full_name} - safe method not available")
                
        return all_features
            
    def _find_feature_matches(self, all_features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find matches between functions based on their features.
        
        Args:
            all_features: Dictionary of function features
            
        Returns:
            List of matches with similarity scores
        """
        matches = []
        functions = list(all_features.keys())
        
        for i in range(len(functions)):
            for j in range(i + 1, len(functions)):
                match = self._compare_function_features(
                    functions[i], functions[j],
                    all_features[functions[i]], all_features[functions[j]]
                )
                if match:
                    matches.append(match)
                    
        return matches
        
    def _compare_function_features(
        self, 
        func1: str, 
        func2: str, 
        features1: Dict[str, Any], 
        features2: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Compare features of two functions.
        
        Args:
            func1: First function name
            func2: Second function name
            features1: Features of first function
            features2: Features of second function
            
        Returns:
            Match information if similarity is above threshold, None otherwise
        """
        common_features = set(features1.keys()) & set(features2.keys())
        if not common_features:
            return None
            
        similarity = len(common_features) / max(len(features1), len(features2))
        
        # Threshold for intent similarity
        if similarity > 0.5:
            return {
                "function1": func1,
                "function2": func2,
                "common_features": list(common_features),
                "similarity": similarity
            }
            
        return None
        
    def _empty_analysis_result(self) -> Dict[str, Any]:
        """Return empty analysis result.
        
        Returns:
            Empty result dictionary
        """
        return {"features": {}, "matches": []}