"""
AST Analyzer for Python code analysis.
"""

import ast
import logging
from typing import List, Optional
from pathlib import Path

from .code_unit import CodeUnit
from .structure_extractor import StructureExtractor

logger = logging.getLogger(__name__)


class ASTAnalyzer:
    """
    Analyzes Python code using AST to extract structural information.
    """
    
    def __init__(self):
        self.extractor = StructureExtractor()
    
    def parse_file(self, file_path: str) -> List[CodeUnit]:
        """
        Parse a Python file and extract code units.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of CodeUnit objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            return self.parse_code(source_code, file_path)
        
        except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
            # These are expected errors that we can handle gracefully
            print(f"❌ Error reading file {file_path}: {e}")
            return []
        except SyntaxError as e:
            # Python syntax errors in the file being analyzed
            print(f"⚠️  Syntax error in {file_path}: {e}")
            return []
    
    def parse_code(self, source_code: str, file_path: Optional[str] = None) -> List[CodeUnit]:
        """
        Parse Python source code and extract code units.
        
        Args:
            source_code: Python source code
            file_path: Optional file path for context
            
        Returns:
            List of CodeUnit objects
        """
        try:
            tree = ast.parse(source_code)
            units = []
            
            # Extract functions and classes only (skip module-level)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    unit = self._create_function_unit(node, source_code, file_path)
                    units.append(unit)
                elif isinstance(node, ast.ClassDef):
                    unit = self._create_class_unit(node, source_code, file_path)
                    units.append(unit)
            
            return units
        
        except SyntaxError as e:
            logger.debug(f"Syntax error in code: {e}")
            return []
        except Exception as e:
            logger.warning(f"Error parsing code: {e}")
            return []
    
    def _create_function_unit(self, node: ast.FunctionDef, source_code: str, 
                             file_path: Optional[str]) -> CodeUnit:
        """Create a code unit for a function."""
        self.extractor.reset()
        self.extractor.visit(node)
        
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
            ast_structure=self.extractor.get_structure_signature(),
            complexity_score=self.extractor.complexity,
            dependencies=list(self.extractor.dependencies)
        )
    
    def _create_class_unit(self, node: ast.ClassDef, source_code: str, 
                          file_path: Optional[str]) -> CodeUnit:
        """Create a code unit for a class."""
        self.extractor.reset()
        self.extractor.visit(node)
        
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
            ast_structure=self.extractor.get_structure_signature(),
            complexity_score=self.extractor.complexity,
            dependencies=list(self.extractor.dependencies)
        )