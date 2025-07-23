"""
AST Structure Extractor Module
Extracts structural information from AST nodes for code analysis.
"""

import ast
from typing import List, Set


class ASTStructureExtractor(ast.NodeVisitor):
    """
    Extracts structural information from AST nodes.
    Focuses on code logic rather than variable names.
    """
    
    def __init__(self):
        self.structure_tokens = []
        self.complexity = 0
        self.dependencies = set()
        self.function_calls = []
        self.imports = []
    
    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        self.structure_tokens.append(f"FUNC:{len(node.args.args)}")
        self.structure_tokens.append(f"DECORATOR:{len(node.decorator_list)}")
        
        # Add detailed argument information
        for i, arg in enumerate(node.args.args):
            if arg.annotation:
                ann_type = self._get_type_name(arg.annotation)
                self.structure_tokens.append(f"ARG_TYPE:{i}:{ann_type}")
            self.structure_tokens.append(f"ARG:{i}:{arg.arg}")
        
        # Add return type if available
        if node.returns:
            ret_type = self._get_type_name(node.returns)
            self.structure_tokens.append(f"RETURN_TYPE:{ret_type}")
        
        self.generic_visit(node)
    
    def _get_type_name(self, annotation):
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
    
    def visit_ClassDef(self, node):
        """Visit class definitions."""
        self.structure_tokens.append(f"CLASS:{len(node.bases)}")
        self.structure_tokens.append(f"DECORATOR:{len(node.decorator_list)}")
        
        # Add base classes
        for base in node.bases:
            if isinstance(base, ast.Name):
                self.structure_tokens.append(f"BASE:{base.id}")
        
        self.generic_visit(node)
    
    def visit_If(self, node):
        """Visit if statements."""
        self.structure_tokens.append("IF")
        self.complexity += 1
        
        # Check for elif and else
        if node.orelse:
            if isinstance(node.orelse[0], ast.If):
                self.structure_tokens.append("ELIF")
            else:
                self.structure_tokens.append("ELSE")
        
        self.generic_visit(node)
    
    def visit_For(self, node):
        """Visit for loops."""
        self.structure_tokens.append("FOR")
        self.complexity += 1
        
        if node.orelse:
            self.structure_tokens.append("FOR_ELSE")
        
        self.generic_visit(node)
    
    def visit_While(self, node):
        """Visit while loops."""
        self.structure_tokens.append("WHILE")
        self.complexity += 1
        
        if node.orelse:
            self.structure_tokens.append("WHILE_ELSE")
        
        self.generic_visit(node)
    
    def visit_Try(self, node):
        """Visit try-except blocks."""
        self.structure_tokens.append("TRY")
        self.complexity += 1
        
        self.structure_tokens.append(f"EXCEPT:{len(node.handlers)}")
        
        if node.orelse:
            self.structure_tokens.append("TRY_ELSE")
        if node.finalbody:
            self.structure_tokens.append("FINALLY")
        
        self.generic_visit(node)
    
    def visit_With(self, node):
        """Visit with statements."""
        self.structure_tokens.append(f"WITH:{len(node.items)}")
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Visit function calls."""
        if isinstance(node.func, ast.Name):
            self.function_calls.append(node.func.id)
            self.structure_tokens.append(f"CALL:{node.func.id}")
            self.dependencies.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            self.function_calls.append(attr_name)
            self.structure_tokens.append(f"CALL:{attr_name}")
            # Add object type for method calls
            if isinstance(node.func.value, ast.Name):
                self.structure_tokens.append(f"METHOD_ON:{node.func.value.id}")
                self.dependencies.add(node.func.value.id)
        
        # Add number of arguments
        self.structure_tokens.append(f"ARGS:{len(node.args)}")
        if node.keywords:
            self.structure_tokens.append(f"KWARGS:{len(node.keywords)}")
            # Add keyword argument names for better matching
            kw_names = [kw.arg for kw in node.keywords if kw.arg]
            if kw_names:
                self.structure_tokens.append(f"KW_NAMES:{','.join(sorted(kw_names))}")
        
        self.generic_visit(node)
    
    def visit_Import(self, node):
        """Visit import statements."""
        for alias in node.names:
            self.imports.append(alias.name)
            self.dependencies.add(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Visit from ... import statements."""
        if node.module:
            self.dependencies.add(node.module)
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_BinOp(self, node):
        """Visit binary operations."""
        op_name = node.op.__class__.__name__
        self.structure_tokens.append(f"BINOP:{op_name}")
        # Add operand types for better matching
        left_type = self._get_node_type(node.left)
        right_type = self._get_node_type(node.right)
        self.structure_tokens.append(f"BINOP_TYPES:{left_type}_{op_name}_{right_type}")
        self.generic_visit(node)
    
    def _get_node_type(self, node):
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
    
    def visit_Compare(self, node):
        """Visit comparisons."""
        for op in node.ops:
            op_name = op.__class__.__name__
            self.structure_tokens.append(f"CMP:{op_name}")
        self.generic_visit(node)
    
    def visit_BoolOp(self, node):
        """Visit boolean operations."""
        op_name = node.op.__class__.__name__
        self.structure_tokens.append(f"BOOL:{op_name}")
        self.generic_visit(node)
    
    def visit_Assign(self, node):
        """Visit assignment statements."""
        # Track assignment patterns
        for target in node.targets:
            if isinstance(target, ast.Name):
                # Track variable assignment with type hint if available
                value_type = self._infer_value_type(node.value)
                self.structure_tokens.append(f"ASSIGN:{target.id}:{value_type}")
            elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
                # Track unpacking assignments
                self.structure_tokens.append(f"UNPACK:{len(target.elts)}")
        self.generic_visit(node)
    
    def _infer_value_type(self, value_node):
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
    
    def visit_UnaryOp(self, node):
        """Visit unary operations."""
        op_name = node.op.__class__.__name__
        self.structure_tokens.append(f"UNARY:{op_name}")
        self.generic_visit(node)
    
    def visit_Return(self, node):
        """Visit return statements."""
        self.structure_tokens.append("RETURN")
        if node.value:
            self.structure_tokens.append("RETURN_VALUE")
            # Add return value type info
            if isinstance(node.value, ast.Name):
                self.structure_tokens.append(f"RETURN_VAR:{node.value.id}")
            elif isinstance(node.value, ast.Constant):
                self.structure_tokens.append(f"RETURN_CONST:{type(node.value.value).__name__}")
            elif isinstance(node.value, ast.List):
                self.structure_tokens.append(f"RETURN_LIST_SIZE:{len(node.value.elts)}")
            elif isinstance(node.value, ast.Dict):
                self.structure_tokens.append(f"RETURN_DICT_SIZE:{len(node.value.keys)}")
            elif isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name):
                    self.structure_tokens.append(f"RETURN_CALL:{node.value.func.id}")
        self.generic_visit(node)
    
    def visit_Raise(self, node):
        """Visit raise statements."""
        self.structure_tokens.append("RAISE")
        self.generic_visit(node)
    
    def visit_Assert(self, node):
        """Visit assert statements."""
        self.structure_tokens.append("ASSERT")
        self.generic_visit(node)
    
    def get_structure_signature(self) -> str:
        """Get a structural signature of the code."""
        return "|".join(self.structure_tokens)