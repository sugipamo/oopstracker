"""Learning statistics management module."""

import logging
from typing import Dict, Any, Optional

from ..intent_tree_fixed_adapter import FixedIntentTreeAdapter


class LearningStatsManager:
    """Manages learning statistics and feature optimization."""
    
    def __init__(self, intent_tree_adapter: FixedIntentTreeAdapter):
        """Initialize learning stats manager.
        
        Args:
            intent_tree_adapter: Intent tree adapter instance
        """
        self.logger = logging.getLogger(__name__)
        self.intent_tree_adapter = intent_tree_adapter
        
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Get learning statistics from the intent tree.
        
        Returns:
            Learning statistics
        """
        if not self.intent_tree_adapter.intent_tree_available:
            return {
                "status": "unavailable",
                "message": "Intent tree is not available",
                "statistics": {}
            }
            
        # Check if adapter has statistics method
        if not hasattr(self.intent_tree_adapter, 'get_learning_statistics'):
            return {
                "status": "unsupported",
                "message": "Learning statistics not supported by intent tree adapter",
                "statistics": {}
            }
            
        # Get statistics from adapter
        stats = await self.intent_tree_adapter.get_learning_statistics()
        
        if not stats:
            return {
                "status": "empty",
                "message": "No learning statistics available",
                "statistics": {}
            }
            
        return {
            "status": "success",
            "message": "Learning statistics retrieved",
            "statistics": stats
        }
        
    async def optimize_features_from_history(self) -> Dict[str, Any]:
        """Optimize features based on learning history.
        
        Returns:
            Optimization results
        """
        if not self.intent_tree_adapter.intent_tree_available:
            return {
                "status": "unavailable",
                "message": "Intent tree is not available",
                "optimization": {}
            }
            
        # Check if adapter has optimization method
        if not hasattr(self.intent_tree_adapter, 'optimize_features'):
            return {
                "status": "unsupported",
                "message": "Feature optimization not supported by intent tree adapter",
                "optimization": {}
            }
            
        # Run optimization
        optimization_result = await self.intent_tree_adapter.optimize_features()
        
        if not optimization_result:
            return {
                "status": "failed",
                "message": "Feature optimization failed",
                "optimization": {}
            }
            
        return {
            "status": "success",
            "message": "Features optimized successfully",
            "optimization": optimization_result
        }
        
    async def get_feature_effectiveness(self) -> Dict[str, Any]:
        """Get effectiveness metrics for current features.
        
        Returns:
            Feature effectiveness metrics
        """
        if not self.intent_tree_adapter.intent_tree_available:
            return {
                "status": "unavailable",
                "features": {}
            }
            
        # Get learning statistics first
        stats = await self.get_learning_statistics()
        
        if stats.get("status") != "success":
            return {
                "status": stats.get("status", "failed"),
                "features": {}
            }
            
        # Extract feature effectiveness from statistics
        feature_stats = stats.get("statistics", {}).get("feature_effectiveness", {})
        
        return {
            "status": "success",
            "features": feature_stats
        }