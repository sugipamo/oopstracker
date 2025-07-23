"""
Specialized AST visitors for different code constructs.
Each visitor focuses on a specific aspect of code analysis.
"""

import ast
from typing import List, Set, Dict, Any


class FunctionVisitor(ast.NodeVisitor):
    """Visitor for analyzing function definitions."""
    
    def __init__(self):
        self.function_signatures = []
        self.decorators = []
        self.argument_types = {}
        self.return_types = {}
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Extract function signature information."""
        sig = {
            'name': node.name,
            'args_count': len(node.args.args),
            'has_varargs': node.args.vararg is not None,
            'has_kwargs': node.args.kwarg is not None,
            'decorator_count': len(node.decorator_list)
        }
        self.function_signatures.append(sig)
        
        # Extract argument types
        for i, arg in enumerate(node.args.args):
            if arg.annotation:
                self.argument_types[f"{node.name}_arg_{i}"] = self._get_type_name(arg.annotation)
        
        # Extract return type
        if node.returns:
            self.return_types[node.name] = self._get_type_name(node.returns)
            
        self.generic_visit(node)
    
    def _get_type_name(self, annotation) -> str:
        """Extract type name from annotation node."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        elif isinstance(annotation, ast.Subscript):
            base = self._get_type_name(annotation.value)
            if hasattr(annotation.slice, 'elts'):
                args = [self._get_type_name(elt) for elt in annotation.slice.elts]
                return f"{base}[{','.join(args)}]"
            else:
                arg = self._get_type_name(annotation.slice)
                return f"{base}[{arg}]"
        return ast.dump(annotation)


class ClassVisitor(ast.NodeVisitor):
    """Visitor for analyzing class definitions."""
    
    def __init__(self):
        self.class_info = []
        self.inheritance_chains = []
        self.method_count = {}
        
    def visit_ClassDef(self, node: ast.ClassDef):
        """Extract class structure information."""
        info = {
            'name': node.name,
            'base_count': len(node.bases),
            'decorator_count': len(node.decorator_list),
            'methods': [],
            'attributes': []
        }
        
        # Count methods and attributes
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                info['methods'].append(item.name)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        info['attributes'].append(target.id)
        
        self.class_info.append(info)
        self.method_count[node.name] = len(info['methods'])
        self.generic_visit(node)


class ControlFlowVisitor(ast.NodeVisitor):
    """Visitor for analyzing control flow structures."""
    
    def __init__(self):
        self.control_patterns = []
        self.nesting_depth = 0
        self.max_nesting = 0
        
    def visit_If(self, node: ast.If):
        """Track if statements and their complexity."""
        self.nesting_depth += 1
        self.max_nesting = max(self.max_nesting, self.nesting_depth)
        
        pattern = f"IF:depth_{self.nesting_depth}"
        if node.orelse:
            pattern += ":has_else"
        self.control_patterns.append(pattern)
        
        self.generic_visit(node)
        self.nesting_depth -= 1
        
    def visit_For(self, node: ast.For):
        """Track for loops."""
        self.nesting_depth += 1
        self.max_nesting = max(self.max_nesting, self.nesting_depth)
        
        pattern = f"FOR:depth_{self.nesting_depth}"
        if node.orelse:
            pattern += ":has_else"
        self.control_patterns.append(pattern)
        
        self.generic_visit(node)
        self.nesting_depth -= 1
        
    def visit_While(self, node: ast.While):
        """Track while loops."""
        self.nesting_depth += 1
        self.max_nesting = max(self.max_nesting, self.nesting_depth)
        
        pattern = f"WHILE:depth_{self.nesting_depth}"
        self.control_patterns.append(pattern)
        
        self.generic_visit(node)
        self.nesting_depth -= 1
        
    def visit_Try(self, node: ast.Try):
        """Track exception handling."""
        pattern = f"TRY:handlers_{len(node.handlers)}"
        if node.else_:
            pattern += ":has_else"
        if node.finalbody:
            pattern += ":has_finally"
        self.control_patterns.append(pattern)
        self.generic_visit(node)


class ExpressionVisitor(ast.NodeVisitor):
    """Visitor for analyzing expressions and operations."""
    
    def __init__(self):
        self.call_targets = []
        self.operators = []
        self.assignments = []
        
    def visit_Call(self, node: ast.Call):
        """Track function calls."""
        if isinstance(node.func, ast.Name):
            self.call_targets.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            # Handle method calls
            if isinstance(node.func.value, ast.Name):
                self.call_targets.append(f"{node.func.value.id}.{node.func.attr}")
        self.generic_visit(node)
        
    def visit_BinOp(self, node: ast.BinOp):
        """Track binary operations."""
        op_name = node.op.__class__.__name__
        self.operators.append(f"BINOP:{op_name}")
        self.generic_visit(node)
        
    def visit_Compare(self, node: ast.Compare):
        """Track comparison operations."""
        for op in node.ops:
            self.operators.append(f"COMPARE:{op.__class__.__name__}")
        self.generic_visit(node)
        
    def visit_Assign(self, node: ast.Assign):
        """Track assignments."""
        target_count = len(node.targets)
        self.assignments.append(f"ASSIGN:targets_{target_count}")
        self.generic_visit(node)