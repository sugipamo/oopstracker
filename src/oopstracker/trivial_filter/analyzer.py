"""
AST analyzer for identifying trivial code patterns.
"""

import ast
from typing import Dict, List


class TrivialPatternAnalyzer(ast.NodeVisitor):
    """
    Analyzes AST nodes to identify trivial patterns that should be excluded from duplication detection.
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset analyzer state."""
        self.return_count = 0
        self.statement_count = 0
        self.has_single_return = False
        self.return_expressions = []
        self.is_pass_only = False
        self.docstring_lines = 0
        self.actual_code_lines = 0
        
    def visit_Return(self, node):
        """Count return statements and analyze their content."""
        self.return_count += 1
        
        if node.value:
            # Analyze return expression
            if isinstance(node.value, ast.Name):
                # return self.property, return variable
                self.return_expressions.append(f"name:{node.value.id}")
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
    
    def analyze_function(self, node: ast.FunctionDef) -> Dict:
        """
        Analyze a function node for trivial patterns.
        
        Returns:
            Dictionary with analysis results
        """
        self.reset()
        self.visit(node)
        
        # Calculate actual code lines (excluding docstring and decorators)
        total_lines = (node.end_lineno or node.lineno) - node.lineno + 1
        
        # Subtract docstring lines from total
        # For actual code complexity, we focus on executable statements
        if self.docstring_lines > 0:
            # Docstring takes up lines, but we want to measure code complexity
            self.actual_code_lines = total_lines - min(self.docstring_lines, total_lines - 2)
        else:
            self.actual_code_lines = total_lines
        
        # For trivial detection, we care more about the statement count
        return {
            'name': node.name,
            'is_special_method': node.name.startswith('__') and node.name.endswith('__'),
            'return_count': self.return_count,
            'statement_count': self.statement_count,
            'has_single_return': self.return_count == 1,
            'return_expressions': self.return_expressions,
            'is_pass_only': self.is_pass_only,
            'total_lines': total_lines,
            'actual_code_lines': self.actual_code_lines,
            'docstring_lines': self.docstring_lines,
            'has_decorator': len(node.decorator_list) > 0,
            'arg_count': len(node.args.args)
        }
    
    def analyze_class(self, node: ast.ClassDef) -> Dict:
        """
        Analyze a class node for trivial patterns.
        
        Returns:
            Dictionary with analysis results
        """
        self.reset()
        self.visit(node)
        
        # Count methods and attributes
        method_count = 0
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                method_count += 1
        
        # Calculate actual code lines
        total_lines = (node.end_lineno or node.lineno) - node.lineno + 1
        self.actual_code_lines = total_lines - self.docstring_lines
        
        return {
            'name': node.name,
            'method_count': method_count,
            'base_count': len(node.bases),
            'statement_count': self.statement_count,
            'is_pass_only': self.is_pass_only,
            'total_lines': total_lines,
            'actual_code_lines': self.actual_code_lines,
            'docstring_lines': self.docstring_lines,
            'has_decorator': len(node.decorator_list) > 0
        }