"""
Factory for creating CodeUnit instances from AST nodes.
Handles the creation logic for different types of code units.
"""

import ast
import logging
from typing import Optional, List
from pathlib import Path
from dataclasses import dataclass

from .ast_structure_extractor import ASTStructureExtractor

logger = logging.getLogger(__name__)


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


class CodeUnitFactory:
    """Factory for creating CodeUnit instances from AST nodes and source code."""
    
    def create_module_unit(self, source_code: str, file_path: Optional[str]) -> CodeUnit:
        """Create a code unit for the entire module."""
        extractor = ASTStructureExtractor()
        
        try:
            tree = ast.parse(source_code)
            extractor.visit(tree)
        except SyntaxError as e:
            logger.debug(f"Syntax error in source code: {e}")
        except Exception as e:
            logger.warning(f"Failed to parse AST: {e}")
        
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
    
    def create_function_unit(self, node: ast.FunctionDef, source_code: str, 
                             file_path: Optional[str]) -> CodeUnit:
        """Create a code unit for a function."""
        extractor = ASTStructureExtractor()
        extractor.visit(node)
        
        # Extract function source code
        lines = source_code.splitlines()
        func_lines = lines[node.lineno - 1:node.end_lineno]
        func_source = '\n'.join(func_lines)
        
        return CodeUnit(
            name=node.name,
            type="function",
            source_code=func_source,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            file_path=file_path,
            ast_structure=extractor.get_structure_signature(),
            complexity_score=extractor.complexity,
            dependencies=list(extractor.dependencies)
        )
    
    def create_class_unit(self, node: ast.ClassDef, source_code: str, 
                          file_path: Optional[str]) -> CodeUnit:
        """Create a code unit for a class."""
        extractor = ASTStructureExtractor()
        extractor.visit(node)
        
        # Extract class source code including decorators
        lines = source_code.splitlines()
        
        # Determine the actual start line (including decorators)
        start_line = node.lineno
        if hasattr(node, 'decorator_list') and node.decorator_list:
            # Use the line number of the first decorator
            start_line = node.decorator_list[0].lineno
        
        class_lines = lines[start_line - 1:node.end_lineno]
        class_source = '\n'.join(class_lines)
        
        return CodeUnit(
            name=node.name,
            type="class",
            source_code=class_source,
            start_line=start_line,
            end_line=node.end_lineno or node.lineno,
            file_path=file_path,
            ast_structure=extractor.get_structure_signature(),
            complexity_score=extractor.complexity,
            dependencies=list(extractor.dependencies)
        )