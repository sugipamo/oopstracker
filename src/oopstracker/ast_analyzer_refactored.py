"""
Refactored AST Analyzer - facade for the new modular AST analysis system.
"""

import ast
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from .ast_analysis import (
    CodeUnit,
    ASTAnalyzer as ModularASTAnalyzer,
    SimilarityCalculator
)

logger = logging.getLogger(__name__)

# Re-export CodeUnit for backward compatibility
__all__ = ['CodeUnit', 'ASTAnalyzer', 'ASTStructureExtractor']


class ASTStructureExtractor:
    """
    Backward compatibility wrapper for the old ASTStructureExtractor.
    This class is deprecated and will be removed in future versions.
    """
    
    def __init__(self):
        logger.warning("ASTStructureExtractor is deprecated. Use ast_analysis.StructureExtractor instead.")
        from .ast_analysis import StructureExtractor
        self._extractor = StructureExtractor()
        
    def __getattr__(self, name):
        """Delegate all attribute access to the new extractor."""
        return getattr(self._extractor, name)


class ASTAnalyzer:
    """
    Facade for the modular AST analysis system.
    Maintains backward compatibility while using the new modular architecture.
    """
    
    def __init__(self):
        self._analyzer = ModularASTAnalyzer()
        self._similarity_calculator = SimilarityCalculator()
    
    def parse_file(self, file_path: str) -> List[CodeUnit]:
        """
        Parse a Python file and extract code units.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of CodeUnit objects
        """
        return self._analyzer.parse_file(file_path)
    
    def parse_code(self, source_code: str, file_path: Optional[str] = None) -> List[CodeUnit]:
        """
        Parse Python source code and extract code units.
        
        Args:
            source_code: Python source code
            file_path: Optional file path for context
            
        Returns:
            List of CodeUnit objects
        """
        return self._analyzer.parse_code(source_code, file_path)
    
    def calculate_structural_similarity(self, unit1: CodeUnit, unit2: CodeUnit) -> float:
        """
        Calculate structural similarity between two code units using Bag of Words.
        
        Args:
            unit1: First code unit
            unit2: Second code unit
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        return self._similarity_calculator.calculate_structural_similarity(unit1, unit2)
    
    def find_similar_units(self, target_unit: CodeUnit, candidate_units: List[CodeUnit], 
                          threshold: float = 0.7) -> List[Tuple[CodeUnit, float]]:
        """
        Find similar code units based on structural similarity.
        
        Args:
            target_unit: Target code unit to find similarities for
            candidate_units: List of candidate units to compare against
            threshold: Minimum similarity threshold
            
        Returns:
            List of (unit, similarity_score) tuples
        """
        return self._similarity_calculator.find_similar_units(target_unit, candidate_units, threshold)
    
    def generate_ast_simhash(self, code_unit: CodeUnit) -> int:
        """
        Generate SimHash based on AST structure.
        
        Args:
            code_unit: Code unit to generate hash for
            
        Returns:
            64-bit SimHash value
        """
        return self._similarity_calculator.generate_ast_simhash(code_unit)
    
    def _create_module_unit(self, source_code: str, file_path: Optional[str]) -> CodeUnit:
        """
        Create a code unit for the entire module.
        This method is kept for backward compatibility but is not used in the new architecture.
        """
        from .ast_analysis import StructureExtractor
        extractor = StructureExtractor()
        
        try:
            tree = ast.parse(source_code)
            extractor.visit(tree)
        except SyntaxError as e:
            print(f"Warning: Syntax error in source code: {e}")
        except Exception as e:
            print(f"Warning: Failed to parse AST: {e}")
        
        return CodeUnit(
            name=Path(file_path).stem if file_path else "module",
            type="module",
            source_code=source_code,
            start_line=1,
            end_line=len(source_code.splitlines()),
            file_path=file_path,
            ast_structure=extractor.get_structure_signature(),
            complexity_score=extractor.complexity,
            dependencies=list(extractor.dependencies)
        )
    
    def _simhash_from_features(self, features: List[str]) -> int:
        """
        Generate SimHash from a list of features.
        This method is kept for backward compatibility.
        
        Args:
            features: List of feature strings
            
        Returns:
            64-bit SimHash value
        """
        return self._similarity_calculator._simhash_from_features(features)