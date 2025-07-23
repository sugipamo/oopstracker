"""
Function Group Clustering System - Refactored implementation.

This module provides a clean interface to the refactored clustering system,
maintaining backward compatibility while leveraging the new modular architecture.
"""

import logging
from typing import List, Dict, Tuple, Any, Optional

from .clustering_models import FunctionGroup, ClusterSplitResult, ClusteringStrategy
from .function_group_clustering.orchestrator import ClusteringOrchestrator


class FunctionGroupClusteringSystem:
    """
    Advanced function clustering system with modular architecture.
    
    This class provides a facade to the refactored clustering components,
    maintaining the original API while using the new implementation.
    """
    
    def __init__(self, enable_ai: bool = True):
        """Initialize the clustering system.
        
        Args:
            enable_ai: Whether to enable AI-based features
        """
        self.logger = logging.getLogger(__name__)
        self.enable_ai = enable_ai
        
        # Initialize the new orchestrator
        self.orchestrator = ClusteringOrchestrator(enable_ai=enable_ai)
        
        # Configuration (for backward compatibility)
        self.min_cluster_size = 3
        self.max_cluster_size = 15
        self.similarity_threshold = 0.7
        
        # Legacy state (for backward compatibility)
        self.split_patterns: Dict[str, Tuple[str, str]] = {}
        
        self.logger.info("Function Group Clustering System initialized (refactored)")
    
    async def load_all_functions_from_repository(self, code_units: List[Any]) -> List[Dict[str, Any]]:
        """Load and prepare function data from code units.
        
        Args:
            code_units: List of code units to process
            
        Returns:
            List of function dictionaries
        """
        functions = []
        
        for unit in code_units:
            if hasattr(unit, 'type') and unit.type == 'function':
                function_data = {
                    'name': unit.name,
                    'code': unit.source_code,
                    'file_path': unit.file_path,
                    'start_line': getattr(unit, 'start_line', 0),
                    'complexity': getattr(unit, 'complexity_score', 0),
                    'hash': getattr(unit, 'code_hash', ''),
                }
                functions.append(function_data)
        
        self.logger.info(f"Loaded {len(functions)} functions from repository")
        return functions
    
    async def get_current_function_clusters(
        self, 
        functions: List[Dict[str, Any]], 
        strategy: ClusteringStrategy = ClusteringStrategy.CATEGORY_BASED
    ) -> List[FunctionGroup]:
        """Group functions into clusters based on the specified strategy.
        
        Args:
            functions: List of function dictionaries
            strategy: Clustering strategy to use
            
        Returns:
            List of function groups
        """
        clusters = await self.orchestrator.cluster_functions(functions, strategy)
        return clusters
    
    async def hierarchical_cluster_and_classify(
        self,
        functions: List[Dict[str, Any]],
        max_group_size: int = 50,
        max_depth: int = 8
    ) -> List[FunctionGroup]:
        """Hierarchically cluster and classify functions.
        
        This method uses the hybrid strategy for hierarchical clustering.
        
        Args:
            functions: List of function dictionaries
            max_group_size: Maximum size before splitting
            max_depth: Maximum recursion depth
            
        Returns:
            List of classified function groups
        """
        # Use hybrid strategy for hierarchical clustering
        clusters = await self.orchestrator.cluster_functions(
            functions, 
            ClusteringStrategy.HYBRID
        )
        
        # The new implementation handles size constraints internally
        self.logger.info(
            f"Hierarchical clustering complete: {len(functions)} functions -> {len(clusters)} groups"
        )
        
        return clusters
    
    def select_clusters_that_need_manual_split(
        self, 
        clusters: List[FunctionGroup]
    ) -> List[FunctionGroup]:
        """Select clusters that need manual splitting based on size and confidence.
        
        Args:
            clusters: List of function groups
            
        Returns:
            List of clusters that need splitting
        """
        candidates = []
        
        for cluster in clusters:
            function_count = len(cluster.functions)
            
            # Size-based selection
            if function_count > self.max_cluster_size:
                candidates.append(cluster)
                continue
            
            # Confidence-based selection
            if cluster.confidence < 0.6:
                candidates.append(cluster)
                continue
            
            # Complexity variance
            complexities = [f.get('complexity', 0) for f in cluster.functions]
            if complexities and len(set(complexities)) > len(complexities) * 0.7:
                candidates.append(cluster)
        
        self.logger.info(f"Selected {len(candidates)} clusters for manual splitting")
        return candidates
    
    def get_clustering_insights(self) -> Dict[str, Any]:
        """Get insights about the current clustering state.
        
        Returns:
            Dictionary of insights
        """
        return self.orchestrator.get_insights()
    
    # Properties for backward compatibility
    @property
    def current_clusters(self) -> List[FunctionGroup]:
        """Get current clusters."""
        return self.orchestrator.current_clusters
    
    @property
    def cluster_history(self) -> List[Dict[str, Any]]:
        """Get cluster history."""
        timeline = self.orchestrator.metadata_recorder.get_clustering_timeline()
        return [t['details'] for t in timeline if t['type'] == 'clustering']
    
    # Additional methods for extended functionality
    
    async def optimize_clusters(self) -> List[FunctionGroup]:
        """Automatically optimize clusters based on insights.
        
        Returns:
            Optimized clusters
        """
        return await self.orchestrator.optimize_clusters()
    
    def get_quality_assessment(self) -> Dict[str, Any]:
        """Get quality assessment of current clusters.
        
        Returns:
            Quality assessment dictionary
        """
        return self.orchestrator.get_quality_assessment()
    
    def get_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations for improving clustering.
        
        Returns:
            List of recommendations
        """
        return self.orchestrator.get_recommendations()
    
    def export_state(self) -> Dict[str, Any]:
        """Export the current state for persistence.
        
        Returns:
            State dictionary
        """
        return self.orchestrator.export_state()
    
    def import_state(self, state: Dict[str, Any]):
        """Import a previously exported state.
        
        Args:
            state: State dictionary to import
        """
        self.orchestrator.import_state(state)