"""
Token builder for AST structure signatures.
"""

from typing import List, Any
import ast


class TokenBuilder:
    """Encapsulates the logic for building structure tokens from AST nodes."""
    
    def __init__(self):
        self.tokens: List[str] = []
    
    def add_function_signature(self, node: ast.FunctionDef):
        """Add tokens for function signature."""
        self.tokens.append(f"FUNC:{len(node.args.args)}")
        self.tokens.append(f"DECORATOR:{len(node.decorator_list)}")
        
        # Add detailed argument information
        for i, arg in enumerate(node.args.args):
            if arg.annotation:
                ann_type = self._get_type_name(arg.annotation)
                self.tokens.append(f"ARG_TYPE:{i}:{ann_type}")
            self.tokens.append(f"ARG:{i}:{arg.arg}")
        
        # Add return type if available
        if node.returns:
            ret_type = self._get_type_name(node.returns)
            self.tokens.append(f"RETURN_TYPE:{ret_type}")
    
    def add_class_signature(self, node: ast.ClassDef):
        """Add tokens for class signature."""
        self.tokens.append(f"CLASS:{len(node.bases)}")
        self.tokens.append(f"DECORATOR:{len(node.decorator_list)}")
        
        # Add base classes
        for base in node.bases:
            if isinstance(base, ast.Name):
                self.tokens.append(f"BASE:{base.id}")
    
    def add_control_flow(self, node_type: str, has_else: bool = False):
        """Add tokens for control flow structures."""
        self.tokens.append(node_type)
        if has_else:
            self.tokens.append(f"{node_type}_ELSE")
    
    def add_loop(self, loop_type: str, has_else: bool = False):
        """Add tokens for loop structures."""
        self.tokens.append(loop_type)
        if has_else:
            self.tokens.append(f"{loop_type}_ELSE")
    
    def add_exception_handling(self, num_handlers: int, has_else: bool = False, has_finally: bool = False):
        """Add tokens for exception handling."""
        self.tokens.append("TRY")
        self.tokens.append(f"EXCEPT:{num_handlers}")
        if has_else:
            self.tokens.append("TRY_ELSE")
        if has_finally:
            self.tokens.append("FINALLY")
    
    def add_context_manager(self, num_items: int):
        """Add tokens for context manager (with statement)."""
        self.tokens.append(f"WITH:{num_items}")
    
    def add_function_call(self, func_name: str, num_args: int, num_kwargs: int = 0, 
                         method_on: str = None, kw_names: List[str] = None):
        """Add tokens for function/method calls."""
        self.tokens.append(f"CALL:{func_name}")
        if method_on:
            self.tokens.append(f"METHOD_ON:{method_on}")
        self.tokens.append(f"ARGS:{num_args}")
        if num_kwargs > 0:
            self.tokens.append(f"KWARGS:{num_kwargs}")
            if kw_names:
                self.tokens.append(f"KW_NAMES:{','.join(sorted(kw_names))}")
    
    def add_binary_operation(self, op_name: str, left_type: str, right_type: str):
        """Add tokens for binary operations."""
        self.tokens.append(f"BINOP:{op_name}")
        self.tokens.append(f"BINOP_TYPES:{left_type}_{op_name}_{right_type}")
    
    def add_comparison(self, op_name: str):
        """Add tokens for comparison operations."""
        self.tokens.append(f"CMP:{op_name}")
    
    def add_boolean_operation(self, op_name: str):
        """Add tokens for boolean operations."""
        self.tokens.append(f"BOOL:{op_name}")
    
    def add_assignment(self, target_name: str, value_type: str):
        """Add tokens for assignments."""
        self.tokens.append(f"ASSIGN:{target_name}:{value_type}")
    
    def add_unpacking(self, num_targets: int):
        """Add tokens for unpacking assignments."""
        self.tokens.append(f"UNPACK:{num_targets}")
    
    def add_unary_operation(self, op_name: str):
        """Add tokens for unary operations."""
        self.tokens.append(f"UNARY:{op_name}")
    
    def add_return(self, return_type: str = None, return_details: str = None):
        """Add tokens for return statements."""
        self.tokens.append("RETURN")
        if return_type:
            self.tokens.append("RETURN_VALUE")
            if return_details:
                self.tokens.append(return_details)
    
    def add_raise(self):
        """Add token for raise statement."""
        self.tokens.append("RAISE")
    
    def add_assert(self):
        """Add token for assert statement."""
        self.tokens.append("ASSERT")
    
    def get_signature(self) -> str:
        """Get the complete structure signature."""
        return "|".join(self.tokens)
    
    def clear(self):
        """Clear all tokens."""
        self.tokens.clear()
    
    def _get_type_name(self, annotation: Any) -> str:
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