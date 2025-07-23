"""
Value object for similarity results.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from .code_record import CodeRecord


@dataclass
class SimilarityResult:
    """Value object representing the result of a code similarity check."""
    
    is_duplicate: bool
    similarity_score: float
    matched_records: List[CodeRecord]
    analysis_method: str = "unknown"
    threshold: float = 1.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if not self.matched_records:
            self.matched_records = []
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_duplicate": self.is_duplicate,
            "similarity_score": self.similarity_score,
            "matched_records": [record.to_dict() if hasattr(record, 'to_dict') else record for record in self.matched_records],
            "analysis_method": self.analysis_method,
            "threshold": self.threshold,
            "metadata": self.metadata,
        }
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to the result."""
        self.metadata[key] = value