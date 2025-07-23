"""Base visitor class for AST structure extraction."""
import ast
from typing import List, Set, Optional


class BaseStructureVisitor(ast.NodeVisitor):
    """
    Base class for AST structure extraction visitors.
    Provides common functionality for all specialized visitors.
    """
    
    def __init__(self):
        self.structure_tokens: List[str] = []
        self.complexity: int = 0
        self.dependencies: Set[str] = set()
        self.function_calls: List[str] = []
        self.imports: List[str] = []
    
    def get_structure_signature(self) -> str:
        """Get a structural signature of the code."""
        return "|".join(self.structure_tokens)
    
    def clear(self):
        """Clear all collected data."""
        self.structure_tokens.clear()
        self.complexity = 0
        self.dependencies.clear()
        self.function_calls.clear()
        self.imports.clear()
    
    def _get_type_name(self, annotation) -> str:
        """Extract type name from annotation node."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        elif isinstance(annotation, ast.Subscript):
            # Handle List[str], Dict[str, int], etc.
            base = self._get_type_name(annotation.value)
            if hasattr(annotation.slice, 'elts'):
                args = [self._get_type_name(elt) for elt in annotation.slice.elts]
                return f"{base}[{','.join(args)}]"
            else:
                arg = self._get_type_name(annotation.slice)
                return f"{base}[{arg}]"
        return ast.dump(annotation)
    
    def _get_node_type(self, node) -> str:
        """Get simplified node type for structure tokens."""
        if isinstance(node, ast.Name):
            return "var"
        elif isinstance(node, ast.Constant):
            return type(node.value).__name__
        elif isinstance(node, ast.Call):
            return "call"
        elif isinstance(node, ast.List):
            return "list"
        elif isinstance(node, ast.Dict):
            return "dict"
        elif isinstance(node, ast.BinOp):
            return "binop"
        return "expr"
    
    def _infer_value_type(self, value_node) -> str:
        """Infer type from value node."""
        if isinstance(value_node, ast.Constant):
            return type(value_node.value).__name__
        elif isinstance(value_node, ast.Name):
            return f"var:{value_node.id}"
        elif isinstance(value_node, ast.Call):
            if isinstance(value_node.func, ast.Name):
                return f"call:{value_node.func.id}"
        elif isinstance(value_node, ast.List):
            return "list"
        elif isinstance(value_node, ast.Dict):
            return "dict"
        elif isinstance(value_node, ast.Set):
            return "set"
        return "unknown"