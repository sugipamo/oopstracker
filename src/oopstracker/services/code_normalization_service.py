"""
Code Normalization Service - Extracted from duplicated implementations.
Implements the Extract pattern to centralize code normalization logic.
Preserves existing oopstracker normalization behavior.
"""

import ast
import re
import logging
from typing import Optional

from ..exceptions import CodeAnalysisError


class CodeNormalizationService:
    """
    Centralized service for code normalization operations.
    
    This service extracts the duplicated code normalization logic that was
    scattered across core.py:25-58, simhash_detector.py:211-244, and 
    domain/code_analysis_engine.py:36-117.
    
    Preserves the exact normalization behavior from the original implementations.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def normalize_code(self, code: str) -> str:
        """
        Normalize code by removing comments, extra whitespace, and standardizing format.
        Extracted from the original duplicated implementations.
        
        Args:
            code: Raw Python code string
            
        Returns:
            Normalized code string
            
        Raises:
            CodeAnalysisError: If normalization fails unexpectedly
        """
        if not code or not code.strip():
            return ""
            
        # Remove comments
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        
        # Parse and reformat with AST if possible
        # If AST parsing fails, continue with basic normalization
        try:
            tree = ast.parse(code)
            normalized = ast.unparse(tree)
        except SyntaxError:
            # AST parsing failed, use the code as-is for remaining normalization
            normalized = code
        
        # Remove extra whitespace (common to both paths)
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = normalized.strip()
        
        return normalized
    
    def normalize_with_metadata(self, code: str) -> dict:
        """
        Normalize code and return normalization metadata.
        
        Args:
            code: Raw code string
            
        Returns:
            Dict containing normalized code and metadata
        """
        original_lines = len(code.splitlines()) if code else 0
        normalized = self.normalize_code(code)
        normalized_lines = len(normalized.splitlines()) if normalized else 0
        
        return {
            "original_code": code,
            "normalized_code": normalized,
            "original_lines": original_lines,
            "normalized_lines": normalized_lines,
            "compression_ratio": normalized_lines / original_lines if original_lines > 0 else 0
        }