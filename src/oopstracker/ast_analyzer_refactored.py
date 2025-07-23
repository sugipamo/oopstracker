"""
Refactored AST Analyzer - Bridge pattern implementation.
Delegates responsibilities to specialized modules in ast_analysis package.
"""

import ast
import logging
from typing import List, Optional

from .ast_analysis import (
    CodeUnit,
    ASTAnalyzer as ModularAnalyzer,
    SimilarityCalculator
)

logger = logging.getLogger(__name__)


class ASTAnalyzer:
    """
    Bridge class that provides backward compatibility while using new modular implementation.
    Acts as a facade to the refactored AST analysis modules.
    """
    
    def __init__(self):
        # Bridge to new modular implementation
        self._analyzer = ModularAnalyzer()
        self._similarity_calculator = SimilarityCalculator()
        
    def parse_file(self, file_path: str) -> List[CodeUnit]:
        """Parse a Python file and extract code units."""
        return self._analyzer.parse_file(file_path)
        
    def parse_code(self, source_code: str, file_path: Optional[str] = None) -> List[CodeUnit]:
        """Parse source code and extract code units."""
        return self._analyzer.parse_code(source_code, file_path)
        
    def calculate_structural_similarity(self, unit1: CodeUnit, unit2: CodeUnit) -> float:
        """Calculate structural similarity between two code units."""
        return self._similarity_calculator.calculate_structural_similarity(unit1, unit2)
        
    def find_similar_units(self, target_unit: CodeUnit, candidate_units: List[CodeUnit], 
                         threshold: float = 0.8) -> List[tuple]:
        """Find units similar to target unit."""
        return self._similarity_calculator.find_similar_units(target_unit, candidate_units, threshold)
        
    def generate_ast_simhash(self, code_unit: CodeUnit) -> int:
        """Generate SimHash from AST structure for fast similarity detection."""
        return self._similarity_calculator.generate_ast_simhash(code_unit)


# Legacy compatibility - Import from original if needed
from .ast_analyzer_original import ASTStructureExtractor

__all__ = ['ASTAnalyzer', 'CodeUnit', 'ASTStructureExtractor']