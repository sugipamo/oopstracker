"""Base class for clustering strategies."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ...clustering_models import FunctionGroup


class ClusterStrategy(ABC):
    """Abstract base class for clustering strategies."""
    
    def __init__(self, enable_ai: bool = True):
        """Initialize the clustering strategy.
        
        Args:
            enable_ai: Whether to enable AI-based features
        """
        self.enable_ai = enable_ai
        
    @abstractmethod
    async def cluster(self, functions: List[Dict[str, Any]]) -> List[FunctionGroup]:
        """Cluster functions based on the specific strategy.
        
        Args:
            functions: List of function dictionaries with metadata
            
        Returns:
            List of function groups
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of the clustering strategy.
        
        Returns:
            Strategy name as string
        """
        pass