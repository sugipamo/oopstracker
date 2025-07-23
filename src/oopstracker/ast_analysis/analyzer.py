"""
Refactored AST Analyzer with separated responsibilities.
"""

import ast
import logging
from typing import List, Optional
from pathlib import Path

from .models import CodeUnit, ASTFeatures
from .extractors import UnifiedExtractor

logger = logging.getLogger(__name__)


class ASTAnalyzer:
    """
    Main analyzer that orchestrates AST analysis.
    Delegates specific responsibilities to specialized components.
    """
    
    def __init__(self):
        self.extractor = UnifiedExtractor()
        
    def parse_file(self, file_path: str) -> List[CodeUnit]:
        """Parse a Python file and extract code units."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            return self.parse_code(source_code, file_path)
        except (IOError, SyntaxError) as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            return []
            
    def parse_code(self, source_code: str, file_path: Optional[str] = None) -> List[CodeUnit]:
        """Parse source code and extract code units."""
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            logger.error(f"Syntax error in code: {e}")
            return []
            
        code_units = []
        
        # Extract module-level unit
        module_unit = self._create_module_unit(source_code, file_path, tree)
        if module_unit:
            code_units.append(module_unit)
        
        # Extract functions and classes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                unit = self._create_function_unit(node, source_code, file_path, tree)
                if unit:
                    code_units.append(unit)
            elif isinstance(node, ast.ClassDef):
                unit = self._create_class_unit(node, source_code, file_path, tree)
                if unit:
                    code_units.append(unit)
                    
        return code_units
    
    def _create_module_unit(self, source_code: str, file_path: Optional[str], tree: ast.AST) -> Optional[CodeUnit]:
        """Create a code unit for the entire module."""
        try:
            features = self.extractor.extract_features(tree)
            
            return CodeUnit(
                name=Path(file_path).stem if file_path else "module",
                type="module",
                source_code=source_code,
                start_line=1,
                end_line=len(source_code.splitlines()),
                file_path=file_path,
                ast_features=features,
                ast_structure=self._generate_structure_signature(features)
            )
        except Exception as e:
            logger.error(f"Error creating module unit: {e}")
            return None
    
    def _create_function_unit(self, node: ast.FunctionDef, source_code: str, 
                            file_path: Optional[str], tree: ast.AST) -> Optional[CodeUnit]:
        """Create a code unit for a function."""
        try:
            # Extract just this function's AST
            func_source = ast.get_source_segment(source_code, node)
            if not func_source:
                return None
                
            func_tree = ast.parse(func_source)
            features = self.extractor.extract_features(func_tree)
            
            return CodeUnit(
                name=node.name,
                type="function",
                source_code=func_source,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                file_path=file_path,
                ast_features=features,
                ast_structure=self._generate_structure_signature(features)
            )
        except Exception as e:
            logger.error(f"Error creating function unit {node.name}: {e}")
            return None
    
    def _create_class_unit(self, node: ast.ClassDef, source_code: str,
                         file_path: Optional[str], tree: ast.AST) -> Optional[CodeUnit]:
        """Create a code unit for a class."""
        try:
            # Extract just this class's AST
            class_source = ast.get_source_segment(source_code, node)
            if not class_source:
                return None
                
            class_tree = ast.parse(class_source)
            features = self.extractor.extract_features(class_tree)
            
            return CodeUnit(
                name=node.name,
                type="class",
                source_code=class_source,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                file_path=file_path,
                ast_features=features,
                ast_structure=self._generate_structure_signature(features)
            )
        except Exception as e:
            logger.error(f"Error creating class unit {node.name}: {e}")
            return None
    
    def _generate_structure_signature(self, features: ASTFeatures) -> str:
        """Generate a unique signature from AST features."""
        # Combine all structural elements
        signature_parts = []
        signature_parts.extend(features.structure_tokens)
        signature_parts.extend(features.control_flow_patterns)
        signature_parts.append(f"COMPLEXITY:{features.complexity_score}")
        
        # Sort for consistency
        signature_parts.sort()
        
        return "|".join(signature_parts)