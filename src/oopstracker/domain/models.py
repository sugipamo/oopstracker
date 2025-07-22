"""
Domain models - Core business entities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum


class DetectionMethod(Enum):
    SIMHASH = "simhash"
    AST = "ast"
    HYBRID = "hybrid"


@dataclass
class CodeUnit:
    """Core domain model for code analysis."""
    content: str
    function_name: Optional[str] = None
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    # Computed fields
    content_hash: Optional[str] = None
    simhash: Optional[int] = None
    normalized_content: Optional[str] = None
    
    def __post_init__(self):
        if not self.content or not self.content.strip():
            raise ValueError("Code content cannot be empty")


@dataclass
class AnalysisConfig:
    """Configuration for code analysis."""
    detection_method: DetectionMethod = DetectionMethod.HYBRID
    simhash_threshold: int = 10
    include_tests: bool = False
    use_ai_analysis: bool = True
    ai_timeout: float = 30.0
    
    # Database config
    db_path: str = "oopstracker.db"
    create_tables: bool = True