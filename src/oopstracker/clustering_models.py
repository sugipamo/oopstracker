"""
Data models for function group clustering system.

This module contains the data structures used throughout the clustering system.
"""

from typing import List, Dict, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum


@dataclass
class FunctionGroup:
    """Represents a group of functionally related functions."""
    group_id: str
    functions: List[Dict[str, Any]]
    label: str
    confidence: float
    primary_patterns: List[str] = None
    risk_level: str = "low"
    split_patterns: Optional[Tuple[str, str]] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.primary_patterns is None:
            self.primary_patterns = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ClusterSplitResult:
    """Result of splitting a cluster using regex patterns."""
    original_cluster_id: str
    group_a: FunctionGroup
    group_b: FunctionGroup
    unmatched: List[Dict[str, Any]]
    split_patterns: Tuple[str, str]
    evaluation_scores: Tuple[float, float]


class ClusteringStrategy(Enum):
    """Available clustering strategies."""
    SEMANTIC_SIMILARITY = "semantic_similarity"
    CATEGORY_BASED = "category_based"
    REGEX_PATTERN = "regex_pattern"
    HYBRID = "hybrid"