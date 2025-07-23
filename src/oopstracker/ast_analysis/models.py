"""
Data models for AST analysis.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ASTFeatures:
    """Features extracted from AST analysis."""
    
    structure_tokens: List[str] = field(default_factory=list)
    complexity_score: int = 0
    dependencies: List[str] = field(default_factory=list)
    function_calls: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    control_flow_patterns: List[str] = field(default_factory=list)
    type_annotations: Dict[str, str] = field(default_factory=dict)
    

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
    ast_features: Optional[ASTFeatures] = None
    ast_structure: Optional[str] = None
    
    @property
    def complexity_score(self) -> int:
        """Get complexity score from AST features."""
        return self.ast_features.complexity_score if self.ast_features else 0
    
    @property
    def dependencies(self) -> List[str]:
        """Get dependencies from AST features."""
        return self.ast_features.dependencies if self.ast_features else []