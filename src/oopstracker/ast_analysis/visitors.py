"""
Specialized AST visitors for different node types.
"""

import ast
from typing import Set, List
from .token_builder import TokenBuilder


class BaseASTVisitor(ast.NodeVisitor):
    """Base class for AST visitors."""
    
    def __init__(self, token_builder: TokenBuilder):
        self.token_builder = token_builder
        self.complexity = 0
        self.dependencies: Set[str] = set()
        self.function_calls: List[str] = []
        self.imports: List[str] = []


class ControlFlowVisitor(BaseASTVisitor):
    """Visitor for control flow structures."""
    
    def visit_If(self, node: ast.If):
        """Visit if statements."""
        self.token_builder.add_control_flow("IF")
        self.complexity += 1
        
        # Check for elif and else
        if node.orelse:
            if isinstance(node.orelse[0], ast.If):
                self.token_builder.add_control_flow("ELIF")
            else:
                self.token_builder.add_control_flow("ELSE")
        
        self.generic_visit(node)
    
    def visit_For(self, node: ast.For):
        """Visit for loops."""
        self.token_builder.add_loop("FOR", has_else=bool(node.orelse))
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_While(self, node: ast.While):
        """Visit while loops."""
        self.token_builder.add_loop("WHILE", has_else=bool(node.orelse))
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_Try(self, node: ast.Try):
        """Visit try-except blocks."""
        self.token_builder.add_exception_handling(
            num_handlers=len(node.handlers),
            has_else=bool(node.orelse),
            has_finally=bool(node.finalbody)
        )
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_With(self, node: ast.With):
        """Visit with statements."""
        self.token_builder.add_context_manager(len(node.items))
        self.generic_visit(node)


class CallVisitor(BaseASTVisitor):
    """Visitor for function and method calls."""
    
    def visit_Call(self, node: ast.Call):
        """Visit function calls."""
        if isinstance(node.func, ast.Name):
            self.function_calls.append(node.func.id)
            self.dependencies.add(node.func.id)
            
            kw_names = [kw.arg for kw in node.keywords if kw.arg]
            self.token_builder.add_function_call(
                func_name=node.func.id,
                num_args=len(node.args),
                num_kwargs=len(node.keywords),
                kw_names=kw_names if kw_names else None
            )
            
        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            self.function_calls.append(attr_name)
            
            method_on = None
            if isinstance(node.func.value, ast.Name):
                method_on = node.func.value.id
                self.dependencies.add(node.func.value.id)
            
            kw_names = [kw.arg for kw in node.keywords if kw.arg]
            self.token_builder.add_function_call(
                func_name=attr_name,
                num_args=len(node.args),
                num_kwargs=len(node.keywords),
                method_on=method_on,
                kw_names=kw_names if kw_names else None
            )
        
        self.generic_visit(node)


class OperatorVisitor(BaseASTVisitor):
    """Visitor for operators and expressions."""
    
    def visit_BinOp(self, node: ast.BinOp):
        """Visit binary operations."""
        op_name = node.op.__class__.__name__
        left_type = self._get_node_type(node.left)
        right_type = self._get_node_type(node.right)
        self.token_builder.add_binary_operation(op_name, left_type, right_type)
        self.generic_visit(node)
    
    def visit_Compare(self, node: ast.Compare):
        """Visit comparisons."""
        for op in node.ops:
            op_name = op.__class__.__name__
            self.token_builder.add_comparison(op_name)
        self.generic_visit(node)
    
    def visit_BoolOp(self, node: ast.BoolOp):
        """Visit boolean operations."""
        op_name = node.op.__class__.__name__
        self.token_builder.add_boolean_operation(op_name)
        self.generic_visit(node)
    
    def visit_UnaryOp(self, node: ast.UnaryOp):
        """Visit unary operations."""
        op_name = node.op.__class__.__name__
        self.token_builder.add_unary_operation(op_name)
        self.generic_visit(node)
    
    def _get_node_type(self, node: ast.AST) -> str:
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


class AssignmentVisitor(BaseASTVisitor):
    """Visitor for assignments and variable operations."""
    
    def visit_Assign(self, node: ast.Assign):
        """Visit assignment statements."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                value_type = self._infer_value_type(node.value)
                self.token_builder.add_assignment(target.id, value_type)
            elif isinstance(target, (ast.Tuple, ast.List)):
                self.token_builder.add_unpacking(len(target.elts))
        self.generic_visit(node)
    
    def visit_Return(self, node: ast.Return):
        """Visit return statements."""
        if not node.value:
            self.token_builder.add_return()
        else:
            return_details = self._get_return_details(node.value)
            self.token_builder.add_return("VALUE", return_details)
        self.generic_visit(node)
    
    def visit_Raise(self, node: ast.Raise):
        """Visit raise statements."""
        self.token_builder.add_raise()
        self.generic_visit(node)
    
    def visit_Assert(self, node: ast.Assert):
        """Visit assert statements."""
        self.token_builder.add_assert()
        self.generic_visit(node)
    
    def _infer_value_type(self, value_node: ast.AST) -> str:
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
    
    def _get_return_details(self, value: ast.AST) -> str:
        """Get details about return value."""
        if isinstance(value, ast.Name):
            return f"RETURN_VAR:{value.id}"
        elif isinstance(value, ast.Constant):
            return f"RETURN_CONST:{type(value.value).__name__}"
        elif isinstance(value, ast.List):
            return f"RETURN_LIST_SIZE:{len(value.elts)}"
        elif isinstance(value, ast.Dict):
            return f"RETURN_DICT_SIZE:{len(value.keys)}"
        elif isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            return f"RETURN_CALL:{value.func.id}"
        return ""


class ImportVisitor(BaseASTVisitor):
    """Visitor for import statements."""
    
    def visit_Import(self, node: ast.Import):
        """Visit import statements."""
        for alias in node.names:
            self.imports.append(alias.name)
            self.dependencies.add(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from ... import statements."""
        if node.module:
            self.dependencies.add(node.module)
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)