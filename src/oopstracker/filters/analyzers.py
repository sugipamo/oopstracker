"""
AST-based analyzers for trivial pattern detection.
"""

import ast
from typing import Dict, Any, List, Optional


class TrivialPatternAnalyzer(ast.NodeVisitor):
    """AST visitor for analyzing code patterns."""
    
    def __init__(self):
        self.has_return = False
        self.has_yield = False
        self.statement_count = 0
        self.max_depth = 0
        self.current_depth = 0
        self.has_docstring = False
        self.is_single_expression = False
        self.uses_self = False
        self.uses_cls = False
        self.calls_super = False
        self.raises_exception = False
        self.has_decorators = False
        self.decorator_names = []
        self.assigned_attributes = []
        self.is_property_getter = False
        self.is_property_setter = False
        self.is_simple_delegation = False
        self.has_loops = False
        self.has_conditionals = False
        self.has_try_except = False
        self.has_with_statement = False
        self.has_assert = False
        self.function_calls = []
        self.imported_names = []
        
    def visit(self, node):
        """Visit a node and track depth."""
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)
        result = super().visit(node)
        self.current_depth -= 1
        return result
        
    def generic_visit(self, node):
        """Count statements as we visit."""
        if isinstance(node, ast.stmt) and not isinstance(node, ast.FunctionDef):
            self.statement_count += 1
        super().generic_visit(node)
    
    def visit_Return(self, node):
        self.has_return = True
        if node.value:
            if isinstance(node.value, ast.Name):
                self.is_single_expression = True
            elif isinstance(node.value, ast.Attribute):
                if isinstance(node.value.value, ast.Name) and node.value.value.id == 'self':
                    self.is_property_getter = True
                    self.is_single_expression = True
        self.generic_visit(node)
        
    def visit_Yield(self, node):
        self.has_yield = True
        self.generic_visit(node)
        
    def visit_YieldFrom(self, node):
        self.has_yield = True
        self.generic_visit(node)
        
    def visit_Name(self, node):
        if node.id == 'self':
            self.uses_self = True
        elif node.id == 'cls':
            self.uses_cls = True
        self.generic_visit(node)
        
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id == 'super':
                self.calls_super = True
            self.function_calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.function_calls.append(node.func.attr)
            # Check for simple delegation pattern
            if (isinstance(node.func.value, ast.Attribute) and 
                isinstance(node.func.value.value, ast.Name) and 
                node.func.value.value.id == 'self'):
                self.is_simple_delegation = True
        self.generic_visit(node)
        
    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                if target.value.id == 'self':
                    self.assigned_attributes.append(target.attr)
        self.generic_visit(node)
        
    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Attribute) and isinstance(node.target.value, ast.Name):
            if node.target.value.id == 'self':
                self.assigned_attributes.append(node.target.attr)
        self.generic_visit(node)
    
    def visit_For(self, node):
        self.has_loops = True
        self.generic_visit(node)
    
    def visit_While(self, node):
        self.has_loops = True
        self.generic_visit(node)
    
    def visit_If(self, node):
        self.has_conditionals = True
        self.generic_visit(node)
    
    def visit_Try(self, node):
        self.has_try_except = True
        self.generic_visit(node)
    
    def visit_With(self, node):
        self.has_with_statement = True
        self.generic_visit(node)
    
    def visit_Raise(self, node):
        self.raises_exception = True
        self.generic_visit(node)
    
    def visit_Assert(self, node):
        self.has_assert = True
        self.generic_visit(node)
    
    def analyze_function(self, node: ast.FunctionDef) -> dict:
        """Analyze a function node and return pattern information."""
        # Reset state
        self.__init__()
        
        # Check for decorators
        if node.decorator_list:
            self.has_decorators = True
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    self.decorator_names.append(decorator.id)
                elif isinstance(decorator, ast.Attribute):
                    self.decorator_names.append(decorator.attr)
        
        # Check for docstring
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            self.has_docstring = True
            # Adjust statement count and body for analysis
            body_without_docstring = node.body[1:]
        else:
            body_without_docstring = node.body
        
        # Visit the function body
        for stmt in body_without_docstring:
            self.visit(stmt)
        
        return {
            'name': node.name,
            'has_return': self.has_return,
            'has_yield': self.has_yield,
            'statement_count': self.statement_count,
            'max_depth': self.max_depth,
            'has_docstring': self.has_docstring,
            'is_single_expression': self.is_single_expression,
            'uses_self': self.uses_self,
            'uses_cls': self.uses_cls,
            'calls_super': self.calls_super,
            'raises_exception': self.raises_exception,
            'has_decorators': self.has_decorators,
            'decorator_names': self.decorator_names,
            'assigned_attributes': self.assigned_attributes,
            'is_property_getter': self.is_property_getter,
            'is_property_setter': self.is_property_setter,
            'is_simple_delegation': self.is_simple_delegation,
            'has_loops': self.has_loops,
            'has_conditionals': self.has_conditionals,
            'has_try_except': self.has_try_except,
            'has_with_statement': self.has_with_statement,
            'has_assert': self.has_assert,
            'function_calls': self.function_calls,
            'line_count': node.end_lineno - node.lineno + 1 if node.end_lineno else 1
        }
    
    def analyze_class(self, node: ast.ClassDef) -> dict:
        """Analyze a class node and return pattern information."""
        methods = []
        attributes = []
        class_variables = []
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                attributes.append(item.target.id)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_variables.append(target.id)
        
        has_dataclass_decorator = any(
            (isinstance(d, ast.Name) and d.id == 'dataclass') or
            (isinstance(d, ast.Attribute) and d.attr == 'dataclass')
            for d in node.decorator_list
        )
        
        return {
            'name': node.name,
            'methods': methods,
            'attributes': attributes,
            'class_variables': class_variables,
            'base_classes': [base.id if isinstance(base, ast.Name) else str(base) for base in node.bases],
            'has_dataclass_decorator': has_dataclass_decorator,
            'decorator_count': len(node.decorator_list),
            'method_count': len(methods),
            'line_count': node.end_lineno - node.lineno + 1 if node.end_lineno else 1
        }