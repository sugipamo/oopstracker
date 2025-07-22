"""
Data models for OOPStracker.
"""

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple


@dataclass
class CodeRecord:
    """Represents a code record stored in the database."""
    
    id: Optional[int] = None
    code_hash: Optional[str] = None
    code_content: Optional[str] = None
    normalized_code: Optional[str] = None
    function_name: Optional[str] = None
    file_path: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    simhash: Optional[int] = None  # Added for SimHash-based similarity
    similarity_score: Optional[float] = None  # Added for similarity results
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}
    
    def generate_hash(self) -> str:
        """Generate SHA-256 hash for the code content."""
        if self.normalized_code:
            content = self.normalized_code
        else:
            content = self.code_content or ""
        
        self.code_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        return self.code_hash
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "code_hash": self.code_hash,
            "code_content": self.code_content,
            "normalized_code": self.normalized_code,
            "function_name": self.function_name,
            "file_path": self.file_path,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata,
            "simhash": self.simhash,
            "similarity_score": self.similarity_score,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeRecord':
        """Create instance from dictionary."""
        timestamp = None
        if data.get("timestamp"):
            timestamp = datetime.fromisoformat(data["timestamp"])
        
        return cls(
            id=data.get("id"),
            code_hash=data.get("code_hash"),
            code_content=data.get("code_content"),
            normalized_code=data.get("normalized_code"),
            function_name=data.get("function_name"),
            file_path=data.get("file_path"),
            timestamp=timestamp,
            metadata=data.get("metadata", {}),
            simhash=data.get("simhash"),
            similarity_score=data.get("similarity_score"),
        )


@dataclass
class SimilarityResult:
    """Represents the result of a code similarity check."""
    
    is_duplicate: bool
    similarity_score: float
    matched_records: List[CodeRecord]
    analysis_method: str = "sha256"
    threshold: float = 1.0
    
    def __post_init__(self):
        if not self.matched_records:
            self.matched_records = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_duplicate": self.is_duplicate,
            "similarity_score": self.similarity_score,
            "matched_records": [record.to_dict() for record in self.matched_records],
            "analysis_method": self.analysis_method,
            "threshold": self.threshold,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimilarityResult':
        """Create instance from dictionary."""
        matched_records = [
            CodeRecord.from_dict(record_data) 
            for record_data in data.get("matched_records", [])
        ]
        
        return cls(
            is_duplicate=data["is_duplicate"],
            similarity_score=data["similarity_score"],
            matched_records=matched_records,
            analysis_method=data.get("analysis_method", "sha256"),
            threshold=data.get("threshold", 1.0),
        )


@dataclass
class DatabaseConfig:
    """Configuration for database connection."""
    
    db_path: str = "oopstracker.db"
    create_tables: bool = True
    backup_enabled: bool = True
    backup_interval: int = 3600  # seconds
    max_records: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "db_path": self.db_path,
            "create_tables": self.create_tables,
            "backup_enabled": self.backup_enabled,
            "backup_interval": self.backup_interval,
            "max_records": self.max_records,
        }


@dataclass
class AnalysisResult:
    """Base class for all analysis results."""
    success: bool
    result: Any
    confidence: float
    reasoning: str
    metadata: Dict[str, Any]
    processing_time: float


@dataclass
class ClassificationResult:
    """Result of function classification analysis."""
    category: str
    confidence: float
    reasoning: str
    matched_rules: List[str]
    processing_time: float


@dataclass
class SemanticAnalysisResult:
    """Result of semantic analysis operations."""
    code_record_1: 'CodeRecord'
    code_record_2: 'CodeRecord'
    semantic_similarity: float
    confidence: float
    analysis_method: str
    reasoning: str
    processing_time: float


def brand_new_learning_function():
    """Test function for intent_tree learning"""
    data = [1, 2, 3, 4, 5]
    total = sum(data)
    average = total / len(data)
    return {"total": total, "average": average}

