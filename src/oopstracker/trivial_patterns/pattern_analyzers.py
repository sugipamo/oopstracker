"""Pattern analyzers for detecting trivial code patterns."""

import ast
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class FunctionAnalysis:
    """Analysis result for a function."""
    name: str
    statement_count: int
    actual_code_lines: int
    return_count: int
    return_expressions: List[str]
    is_pass_only: bool
    has_decorators: bool
    decorator_names: List[str]
    docstring_lines: int
    is_property: bool
    is_special_method: bool


class TrivialPatternAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze code patterns for triviality detection."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset analysis state."""
        self.statement_count = 0
        self.return_count = 0
        self.return_expressions = []
        self.is_pass_only = False
        self.actual_code_lines = 0
        self.docstring_lines = 0
    
    def visit_Return(self, node):
        """Track return statements and their complexity."""
        self.return_count += 1
        
        if node.value:
            if isinstance(node.value, ast.Name):
                # return variable_name
                self.return_expressions.append(f"var:{node.value.id}")
            elif isinstance(node.value, ast.Attribute):
                # return self.field, return obj.attr
                self.return_expressions.append(f"attr:{node.value.attr}")
            elif isinstance(node.value, ast.Constant):
                # return "constant", return 42
                self.return_expressions.append(f"const:{type(node.value.value).__name__}")
            else:
                # More complex expression
                self.return_expressions.append("complex")
        else:
            # return without value
            self.return_expressions.append("none")
        
        self.generic_visit(node)
    
    def visit_Pass(self, node):
        """Check for pass-only functions/classes."""
        self.is_pass_only = True
        self.generic_visit(node)
    
    def visit_Expr(self, node):
        """Count expression statements (including docstrings)."""
        # Check if this is a docstring
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            # This is likely a docstring - count it but don't add to statement count
            self.docstring_lines += len(node.value.value.splitlines())
        else:
            self.statement_count += 1
        
        self.generic_visit(node)
    
    def visit_Assign(self, node):
        """Count assignment statements."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def visit_AugAssign(self, node):
        """Count augmented assignment statements."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def visit_If(self, node):
        """Count if statements."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def visit_For(self, node):
        """Count for loops."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def visit_While(self, node):
        """Count while loops."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def visit_Try(self, node):
        """Count try blocks."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def visit_With(self, node):
        """Count with statements."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def visit_Raise(self, node):
        """Count raise statements."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def visit_Assert(self, node):
        """Count assert statements."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def analyze_function(self, node: ast.FunctionDef) -> FunctionAnalysis:
        """
        Analyze a function node for trivial patterns.
        
        Args:
            node: AST function definition node
            
        Returns:
            FunctionAnalysis with results
        """
        self.reset()
        self.visit(node)
        
        # Calculate actual code lines (excluding docstring and decorators)
        total_lines = (node.end_lineno or node.lineno) - node.lineno + 1
        
        # Subtract docstring lines from total
        if self.docstring_lines > 0:
            actual_code_lines = total_lines - min(self.docstring_lines, total_lines - 2)
        else:
            actual_code_lines = total_lines
        
        # Check for property decorator
        is_property = any(
            isinstance(d, ast.Name) and d.id == 'property' 
            for d in node.decorator_list
        )
        
        # Extract decorator names
        decorator_names = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorator_names.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorator_names.append(dec.attr)
        
        # Check if this is a special method
        is_special_method = node.name.startswith('__') and node.name.endswith('__')
        
        return FunctionAnalysis(
            name=node.name,
            statement_count=self.statement_count,
            actual_code_lines=actual_code_lines,
            return_count=self.return_count,
            return_expressions=self.return_expressions,
            is_pass_only=self.is_pass_only,
            has_decorators=bool(node.decorator_list),
            decorator_names=decorator_names,
            docstring_lines=self.docstring_lines,
            is_property=is_property,
            is_special_method=is_special_method
        )