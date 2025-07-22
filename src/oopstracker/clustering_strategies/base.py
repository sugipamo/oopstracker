"""
Base class for clustering strategies.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ..clustering_models import FunctionGroup


class ClusteringStrategyBase(ABC):
    """Abstract base class for clustering strategies."""
    
    def __init__(self, min_cluster_size: int = 3, max_cluster_size: int = 15):
        self.min_cluster_size = min_cluster_size
        self.max_cluster_size = max_cluster_size
    
    @abstractmethod
    async def cluster(self, functions: List[Dict[str, Any]]) -> List[FunctionGroup]:
        """
        Cluster functions according to the strategy.
        
        Args:
            functions: List of function dictionaries containing code metadata
            
        Returns:
            List of FunctionGroup objects
        """
        pass
    
    def validate_cluster_size(self, cluster: List[Dict[str, Any]]) -> bool:
        """Validate if cluster size is within acceptable bounds."""
        return self.min_cluster_size <= len(cluster) <= self.max_cluster_size