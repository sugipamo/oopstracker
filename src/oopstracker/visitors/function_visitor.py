"""Visitor for function-related AST nodes."""
import ast
from .base import BaseStructureVisitor


class FunctionVisitor(BaseStructureVisitor):
    """
    Specializes in extracting function-related structural information.
    Handles function definitions, arguments, decorators, and returns.
    """
    
    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        self.structure_tokens.append(f"FUNC:{len(node.args.args)}")
        self.complexity += 1
        
        # Delegate specific processing to dedicated methods
        self._process_decorators(node.decorator_list)
        self._process_arguments(node.args)
        self._process_return_annotation(node.returns)
        
        self.generic_visit(node)
    
    def _process_decorators(self, decorator_list):
        """Process function decorators."""
        self.structure_tokens.append(f"DECORATOR:{len(decorator_list)}")
    
    def _process_arguments(self, args):
        """Process function arguments including types and defaults."""
        # Process positional arguments
        self._process_positional_args(args.args)
        
        # Process keyword-only arguments
        self._process_keyword_only_args(args.kwonlyargs)
        
        # Process defaults
        self._process_defaults(args.defaults, args.kw_defaults)
    
    def _process_positional_args(self, args):
        """Process positional arguments."""
        for i, arg in enumerate(args):
            self._process_single_arg(arg, i, "ARG")
    
    def _process_keyword_only_args(self, kwonlyargs):
        """Process keyword-only arguments."""
        for i, arg in enumerate(kwonlyargs):
            self._process_single_arg(arg, i, "KWARG")
    
    def _process_single_arg(self, arg, index, prefix):
        """Process a single argument with its annotation."""
        self.structure_tokens.append(f"{prefix}:{index}:{arg.arg}")
        if arg.annotation:
            ann_type = self._get_type_name(arg.annotation)
            self.structure_tokens.append(f"{prefix}_TYPE:{index}:{ann_type}")
    
    def _process_defaults(self, defaults, kw_defaults):
        """Process default values for arguments."""
        if defaults:
            self.structure_tokens.append(f"DEFAULTS:{len(defaults)}")
        if kw_defaults and any(d is not None for d in kw_defaults):
            non_none_count = sum(1 for d in kw_defaults if d is not None)
            self.structure_tokens.append(f"KW_DEFAULTS:{non_none_count}")
    
    def _process_return_annotation(self, returns):
        """Process return type annotation."""
        if returns:
            ret_type = self._get_type_name(returns)
            self.structure_tokens.append(f"RETURN_TYPE:{ret_type}")
    
    def visit_AsyncFunctionDef(self, node):
        """Visit async function definitions."""
        self.structure_tokens.append("ASYNC_FUNC")
        # Delegate to regular function handling
        self.visit_FunctionDef(node)
    
    def visit_Lambda(self, node):
        """Visit lambda expressions."""
        self.structure_tokens.append(f"LAMBDA:{len(node.args.args)}")
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Visit function calls."""
        self.complexity += 1
        
        # Delegate to specific call processing methods
        self._process_call_target(node.func)
        self._process_call_arguments(node)
        
        self.generic_visit(node)
    
    def _process_call_target(self, func):
        """Process the target of a function call."""
        if isinstance(func, ast.Name):
            self.structure_tokens.append(f"CALL:{func.id}")
            self.function_calls.append(func.id)
            self._check_builtin_call(func.id)
        elif isinstance(func, ast.Attribute):
            self.structure_tokens.append(f"CALL_ATTR:{func.attr}")
            if isinstance(func.value, ast.Name):
                self.dependencies.add(func.value.id)
        else:
            self.structure_tokens.append("CALL:COMPLEX")
    
    def _check_builtin_call(self, func_name):
        """Check if the function is a builtin."""
        builtins = {'len', 'range', 'enumerate', 'zip', 'map', 'filter'}
        if func_name in builtins:
            self.structure_tokens.append(f"BUILTIN:{func_name}")
    
    def _process_call_arguments(self, node):
        """Process arguments of a function call."""
        self.structure_tokens.append(f"CALL_ARGS:{len(node.args)}")
    
    def visit_Return(self, node):
        """Visit return statements."""
        self.structure_tokens.append("RETURN")
        if node.value:
            self._process_return_value(node.value)
        self.generic_visit(node)
    
    def _process_return_value(self, value):
        """Process the value being returned."""
        self.structure_tokens.append("RETURN_VALUE")
        
        return_type_info = self._get_return_type_info(value)
        if return_type_info:
            self.structure_tokens.append(return_type_info)
    
    def _get_return_type_info(self, value):
        """Get type information for return value."""
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
        return None
    
    def visit_Yield(self, node):
        """Visit yield statements."""
        self.structure_tokens.append("YIELD")
        if node.value:
            self.structure_tokens.append("YIELD_VALUE")
        self.generic_visit(node)
    
    def visit_YieldFrom(self, node):
        """Visit yield from statements."""
        self.structure_tokens.append("YIELD_FROM")
        self.generic_visit(node)