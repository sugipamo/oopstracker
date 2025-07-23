"""
AST structure extractor using visitor pattern.
"""

import ast
from typing import Set, List
from .token_builder import TokenBuilder
from .visitors import (
    ControlFlowVisitor,
    CallVisitor,
    OperatorVisitor,
    AssignmentVisitor,
    ImportVisitor
)


class StructureExtractor(ast.NodeVisitor):
    """
    Extracts structural information from AST nodes.
    Focuses on code logic rather than variable names.
    """
    
    def __init__(self):
        self.token_builder = TokenBuilder()
        self.complexity = 0
        self.dependencies: Set[str] = set()
        self.function_calls: List[str] = []
        self.imports: List[str] = []
        
        # Initialize specialized visitors
        self._control_flow_visitor = ControlFlowVisitor(self.token_builder)
        self._call_visitor = CallVisitor(self.token_builder)
        self._operator_visitor = OperatorVisitor(self.token_builder)
        self._assignment_visitor = AssignmentVisitor(self.token_builder)
        self._import_visitor = ImportVisitor(self.token_builder)
    
    def visit(self, node: ast.AST):
        """Override visit to delegate to specialized visitors."""
        # First, handle this node with the main extractor
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, None)
        if visitor:
            visitor(node)
        else:
            # Delegate to specialized visitors for unhandled nodes
            self._delegate_to_visitors(node)
            self.generic_visit(node)
    
    def _delegate_to_visitors(self, node: ast.AST):
        """Delegate node processing to specialized visitors."""
        # Control flow
        if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
            self._control_flow_visitor.visit(node)
            self._update_metrics(self._control_flow_visitor)
        
        # Function calls
        elif isinstance(node, ast.Call):
            self._call_visitor.visit(node)
            self._update_metrics(self._call_visitor)
        
        # Operators
        elif isinstance(node, (ast.BinOp, ast.Compare, ast.BoolOp, ast.UnaryOp)):
            self._operator_visitor.visit(node)
            self._update_metrics(self._operator_visitor)
        
        # Assignments and returns
        elif isinstance(node, (ast.Assign, ast.Return, ast.Raise, ast.Assert)):
            self._assignment_visitor.visit(node)
            self._update_metrics(self._assignment_visitor)
        
        # Imports
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            self._import_visitor.visit(node)
            self._update_metrics(self._import_visitor)
    
    def _update_metrics(self, visitor):
        """Update metrics from specialized visitor."""
        self.complexity = max(self.complexity, visitor.complexity)
        self.dependencies.update(visitor.dependencies)
        self.function_calls.extend(visitor.function_calls)
        self.imports.extend(visitor.imports)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definitions."""
        self.token_builder.add_function_signature(node)
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definitions."""
        self.token_builder.add_class_signature(node)
        self.generic_visit(node)
    
    def get_structure_signature(self) -> str:
        """Get a structural signature of the code."""
        return self.token_builder.get_signature()
    
    def reset(self):
        """Reset the extractor state."""
        self.token_builder.clear()
        self.complexity = 0
        self.dependencies.clear()
        self.function_calls.clear()
        self.imports.clear()
        
        # Reset specialized visitors
        for visitor in [
            self._control_flow_visitor,
            self._call_visitor,
            self._operator_visitor,
            self._assignment_visitor,
            self._import_visitor
        ]:
            visitor.complexity = 0
            visitor.dependencies.clear()
            visitor.function_calls.clear()
            visitor.imports.clear()