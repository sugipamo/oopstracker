"""
AST-based code analysis for structural similarity detection.
Extracts semantic structure from code for more accurate duplicate detection.
"""

import ast
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from collections import Counter

# Import from new modular structure
from .ast_analysis import (
    ASTStructureExtractor,
    CodeUnit,
    ASTAnalyzer as ModularAnalyzer,
    SimilarityCalculator
)

logger = logging.getLogger(__name__)


# Legacy ASTStructureExtractor - kept for backward compatibility
# The actual implementation is now in ast_analysis.structure_extractor
class ASTStructureExtractor(ASTStructureExtractor):
    """Legacy wrapper for backward compatibility."""
    pass


class ASTAnalyzer:
    """
    Analyzes Python code using AST to extract structural information.
    This is a wrapper around the modular analyzer for backward compatibility.
    """
    
    def __init__(self):
        self._analyzer = ModularAnalyzer()
        self._similarity_calculator = SimilarityCalculator()
        self.extractors = {}
    
    def parse_file(self, file_path: str) -> List[CodeUnit]:
        """Parse a Python file and extract code units."""
        return self._analyzer.parse_file(file_path)
    
    def parse_code(self, source_code: str, file_path: Optional[str] = None) -> List[CodeUnit]:
        """Parse Python source code and extract code units."""
        return self._analyzer.parse_code(source_code, file_path)
    
    def _create_module_unit(self, source_code: str, file_path: Optional[str]) -> CodeUnit:
        """Create a code unit for the entire module."""
        return self._analyzer._create_module_unit(source_code, file_path)
    
    def _create_function_unit(self, node: ast.FunctionDef, source_code: str, 
                             file_path: Optional[str]) -> CodeUnit:
        """Create a code unit for a function."""
        return self._analyzer._create_function_unit(node, source_code, file_path)
    
    def _create_class_unit(self, node: ast.ClassDef, source_code: str, 
                          file_path: Optional[str]) -> CodeUnit:
        """Create a code unit for a class."""
        return self._analyzer._create_class_unit(node, source_code, file_path)
    
    def calculate_structural_similarity(self, unit1: CodeUnit, unit2: CodeUnit) -> float:
        """Calculate structural similarity between two code units."""
        return self._similarity_calculator.calculate_structural_similarity(unit1, unit2)
    
    def find_similar_units(self, target_unit: CodeUnit, candidate_units: List[CodeUnit], 
                          threshold: float = 0.7) -> List[Tuple[CodeUnit, float]]:
        """Find similar code units based on structural similarity."""
        return self._analyzer.find_similar_units(target_unit, candidate_units, threshold)
    
    def generate_ast_simhash(self, code_unit: CodeUnit) -> int:
        """Generate SimHash based on AST structure."""
        return self._similarity_calculator.generate_ast_simhash(code_unit)
    
    def _simhash_from_features(self, features: List[str]) -> int:
        """Generate SimHash from a list of features."""
        return self._similarity_calculator._simhash_from_features(features)