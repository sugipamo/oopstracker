"""
Code unit representation for AST analysis.
"""

from typing import List, Optional
from dataclasses import dataclass


@dataclass
class CodeUnit:
    """Represents a single code unit (function, class, or module)."""
    
    name: str
    type: str  # 'function', 'class', 'module'
    source_code: str
    start_line: int
    end_line: int
    file_path: Optional[str] = None
    
    # AST-derived features
    ast_structure: Optional[str] = None
    complexity_score: Optional[int] = None
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []