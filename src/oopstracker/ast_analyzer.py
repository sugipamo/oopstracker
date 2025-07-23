"""
AST-based code analysis for structural similarity detection.
Extracts semantic structure from code for more accurate duplicate detection.
"""

import ast
import logging
from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass

from .visitors import (
    FunctionVisitor,
    ClassVisitor,
    ControlFlowVisitor,
    ExpressionVisitor
)

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
    hash: Optional[str] = None  # Hash for SimHash calculations
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.hash is None:
            # Generate hash based on content
            import hashlib
            content_for_hash = f"{self.name}:{self.source_code}"
            self.hash = hashlib.md5(content_for_hash.encode()).hexdigest()


class CompositeVisitor:
    """
    Combines multiple specialized visitors to extract comprehensive structural information.
    """
    
    def __init__(self):
        self.visitors = [
            FunctionVisitor(),
            ClassVisitor(),
            ControlFlowVisitor(),
            ExpressionVisitor()
        ]
    
    def visit(self, node):
        """Visit node with all registered visitors."""
        for visitor in self.visitors:
            visitor.visit(node)
    
    def get_structure_signature(self) -> str:
        """Combine structure signatures from all visitors."""
        all_tokens = []
        for visitor in self.visitors:
            tokens = visitor.structure_tokens
            if tokens:
                all_tokens.extend(tokens)
        return "|".join(all_tokens) if all_tokens else ""
    
    def get_complexity_score(self) -> int:
        """Sum complexity scores from all visitors."""
        return sum(visitor.complexity for visitor in self.visitors)
    
    def get_dependencies(self) -> List[str]:
        """Combine dependencies from all visitors."""
        all_deps = set()
        for visitor in self.visitors:
            all_deps.update(visitor.dependencies)
        return list(all_deps)
    
    def clear(self):
        """Clear all visitors."""
        for visitor in self.visitors:
            visitor.clear()


class ASTAnalyzer:
    """
    Analyzes Python code using AST to extract structural information.
    Uses specialized visitors for different aspects of code structure.
    """
    
    def __init__(self):
        self.composite_visitor = CompositeVisitor()
    
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
            logger.info(f"Error reading file {file_path}: {e}")
            return []
        except SyntaxError as e:
            logger.info(f"Syntax error in {file_path}: {e}")
            return []
    
    def extract_code_units(self, source_code: str, file_path: Optional[str] = None) -> List[CodeUnit]:
        """
        Extract code units from Python source code.
        Alias for parse_code for backward compatibility.
        
        Args:
            source_code: Python source code
            file_path: Optional file path for context
            
        Returns:
            List of CodeUnit objects
        """
        return self.parse_code(source_code, file_path)
    
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
            
            # Extract functions and classes
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
        # Clear previous visitor state
        self.composite_visitor.clear()
        
        # Visit the function node
        self.composite_visitor.visit(node)
        
        # Extract source code for the function
        lines = source_code.splitlines()
        func_source = self._extract_node_source(node, lines)
        
        return CodeUnit(
            name=node.name,
            type="function",
            source_code=func_source,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            file_path=file_path,
            ast_structure=self.composite_visitor.get_structure_signature(),
            complexity_score=self.composite_visitor.get_complexity_score(),
            dependencies=self.composite_visitor.get_dependencies()
        )
    
    def _create_class_unit(self, node: ast.ClassDef, source_code: str,
                          file_path: Optional[str]) -> CodeUnit:
        """Create a code unit for a class."""
        # Clear previous visitor state
        self.composite_visitor.clear()
        
        # Visit the class node
        self.composite_visitor.visit(node)
        
        # Extract source code for the class
        lines = source_code.splitlines()
        class_source = self._extract_node_source(node, lines)
        
        return CodeUnit(
            name=node.name,
            type="class",
            source_code=class_source,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            file_path=file_path,
            ast_structure=self.composite_visitor.get_structure_signature(),
            complexity_score=self.composite_visitor.get_complexity_score(),
            dependencies=self.composite_visitor.get_dependencies()
        )
    
    def _extract_node_source(self, node: ast.AST, lines: List[str]) -> str:
        """Extract source code for a specific AST node."""
        if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
            start = node.lineno - 1
            end = node.end_lineno or node.lineno
            
            if 0 <= start < len(lines) and start < end <= len(lines):
                # Get the lines and find the minimum indentation
                node_lines = lines[start:end]
                if node_lines:
                    # Find minimum indentation (excluding empty lines)
                    min_indent = min(
                        (len(line) - len(line.lstrip()) 
                         for line in node_lines if line.strip()),
                        default=0
                    )
                    
                    # Remove the common indentation
                    dedented_lines = [
                        line[min_indent:] if len(line) > min_indent else line
                        for line in node_lines
                    ]
                    
                    return '\n'.join(dedented_lines)
        
        return ""
    
    def get_structure_hash(self, structure_signature: str) -> str:
        """Get a hash of the structure signature for quick comparison."""
        import hashlib
        return hashlib.sha256(structure_signature.encode()).hexdigest()[:16]