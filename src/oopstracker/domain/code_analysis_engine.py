"""
Core analysis engine - Central orchestration of code analysis.
"""

import logging
import hashlib
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .models import CodeUnit, AnalysisConfig
from .detection_strategy import DetectionStrategy, DetectionResult, ConfidenceLevel


class NormalizationMethod(Enum):
    AST = "ast"
    BASIC = "basic"


@dataclass
class NormalizationResult:
    """Result of code normalization operation."""
    success: bool
    normalized_code: str
    method_used: NormalizationMethod
    message: Optional[str] = None


class CodeNormalizationService:
    """Service for code normalization with explicit method selection."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def normalize_code(self, code: str) -> NormalizationResult:
        """Normalize code using the most appropriate method available."""
        # First check if AST normalization is viable
        if self._is_ast_viable(code):
            return self._ast_normalization(code)
        else:
            self.logger.debug("AST normalization not viable, using basic normalization")
            return self._basic_normalization(code)
    
    def _is_ast_viable(self, code: str) -> bool:
        """Check if AST normalization is viable for the given code."""
        # Remove comments first for pre-validation
        clean_code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        
        # Pre-validate: check basic requirements
        if not clean_code.strip():
            return False
        
        # Check for obvious syntax issues
        if clean_code.count('(') != clean_code.count(')'):
            return False
        if clean_code.count('[') != clean_code.count(']'):
            return False
        if clean_code.count('{') != clean_code.count('}'):
            return False
        
        # Check if it looks like Python code
        if not self._looks_like_python(clean_code):
            return False
        
        return True
    
    def _looks_like_python(self, code: str) -> bool:
        """Basic heuristic check if code looks like Python."""
        python_keywords = ['def ', 'class ', 'import ', 'from ', 'if ', 'for ', 'while ', 'return']
        code_lower = code.lower()
        
        # Check for at least one Python keyword or proper indentation pattern
        has_keywords = any(keyword in code_lower for keyword in python_keywords)
        has_proper_structure = ':' in code and ('    ' in code or '\t' in code)
        
        return has_keywords or has_proper_structure
    
    def _ast_normalization(self, code: str) -> NormalizationResult:
        """Perform AST-based normalization."""
        import ast
        
        # Remove comments first
        clean_code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        
        # Parse and reformat using ast module (this is safe to call based on pre-validation)
        tree = ast.parse(clean_code)
        normalized = ast.unparse(tree)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return NormalizationResult(
            success=True,
            normalized_code=normalized,
            method_used=NormalizationMethod.AST,
            message="AST normalization successful"
        )
    
    def _basic_normalization(self, code: str) -> NormalizationResult:
        """Perform basic text normalization."""
        # Remove comments
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        
        # Remove empty lines and normalize whitespace
        lines = [line.strip() for line in code.splitlines() if line.strip()]
        code = '\n'.join(lines)
        
        # Normalize multiple spaces to single space
        normalized = re.sub(r'\s+', ' ', code).strip()
        
        return NormalizationResult(
            success=True,
            normalized_code=normalized,
            method_used=NormalizationMethod.BASIC,
            message="Basic normalization completed"
        )


class CodeAnalysisEngine:
    """Core engine for code analysis orchestration."""
    
    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._strategies: Dict[str, DetectionStrategy] = {}
        self._code_units: List[CodeUnit] = []
        self._normalizer = CodeNormalizationService()
    
    def register_strategy(self, strategy: DetectionStrategy):
        """Register a detection strategy."""
        method_name = strategy.get_method_name()
        self._strategies[method_name] = strategy
        self.logger.info(f"Registered detection strategy: {method_name}")
    
    def register_code_unit(self, code_unit: CodeUnit) -> CodeUnit:
        """Register a new code unit for analysis."""
        # Prepare the code unit
        self._prepare_code_unit(code_unit)
        
        # Add to collection
        self._code_units.append(code_unit)
        
        self.logger.debug(f"Registered code unit: {code_unit.function_name or 'anonymous'}")
        return code_unit
    
    def detect_duplicates(self, code_unit: CodeUnit) -> DetectionResult:
        """Detect duplicates for a given code unit."""
        if not self._strategies:
            raise ValueError("No detection strategies registered")
        
        # Get the primary strategy based on config
        strategy_name = self.config.detection_method.value
        if strategy_name not in self._strategies:
            # Use first available strategy
            strategy_name = next(iter(self._strategies.keys()))
            self.logger.warning(f"Requested strategy '{self.config.detection_method.value}' not available, using '{strategy_name}'")
        
        strategy = self._strategies[strategy_name]
        result = strategy.detect_similarity(code_unit, self._code_units)
        
        self.logger.info(f"Detection completed: {result.is_duplicate} (confidence: {result.confidence.value})")
        return result
    
    def get_all_code_units(self) -> List[CodeUnit]:
        """Get all registered code units."""
        return self._code_units.copy()
    
    def clear_units(self):
        """Clear all registered code units."""
        self._code_units.clear()
        self.logger.info("All code units cleared")
    
    def _prepare_code_unit(self, code_unit: CodeUnit):
        """Prepare code unit for analysis (normalization, hashing, etc.)."""
        # Generate content hash
        code_unit.content_hash = hashlib.sha256(code_unit.content.encode()).hexdigest()
        
        # Normalize content using the normalization service
        norm_result = self._normalizer.normalize_code(code_unit.content)
        code_unit.normalized_content = norm_result.normalized_code
        
        self.logger.debug(f"Code unit prepared: hash={code_unit.content_hash[:8]}... (method: {norm_result.method_used.value})")