"""Visitor for control flow AST nodes."""
import ast
from .base import BaseStructureVisitor


class ControlFlowVisitor(BaseStructureVisitor):
    """
    Specializes in extracting control flow structural information.
    Handles if/else, loops, exception handling, and other control structures.
    """
    
    def visit_If(self, node):
        """Visit if statements."""
        self.structure_tokens.append("IF")
        self.complexity += 1
        
        # Process condition complexity
        self._process_condition(node.test)
        
        # Check for elif and else branches
        has_else = len(node.orelse) > 0
        if has_else:
            self.structure_tokens.append("HAS_ELSE")
            # Check if else contains another if (elif)
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                self.structure_tokens.append("ELIF")
        
        self.generic_visit(node)
    
    def visit_For(self, node):
        """Visit for loops."""
        self.structure_tokens.append("FOR")
        self.complexity += 1
        
        # Check if iterating over common patterns
        self._process_iteration_target(node.iter)
        
        # Check for else clause
        if node.orelse:
            self.structure_tokens.append("FOR_ELSE")
        
        self.generic_visit(node)
    
    def visit_While(self, node):
        """Visit while loops."""
        self.structure_tokens.append("WHILE")
        self.complexity += 1
        
        # Process condition
        self._process_condition(node.test)
        
        # Check for else clause
        if node.orelse:
            self.structure_tokens.append("WHILE_ELSE")
        
        self.generic_visit(node)
    
    def visit_With(self, node):
        """Visit with statements (context managers)."""
        self.structure_tokens.append(f"WITH:{len(node.items)}")
        self.complexity += 1
        
        # Process context manager items
        for item in node.items:
            self._process_with_item(item)
        
        self.generic_visit(node)
    
    def visit_Try(self, node):
        """Visit try/except blocks."""
        self.structure_tokens.append("TRY")
        self.complexity += 1
        
        # Process exception handlers
        self._process_exception_handlers(node.handlers)
        
        # Check for else and finally
        if node.orelse:
            self.structure_tokens.append("TRY_ELSE")
        if node.finalbody:
            self.structure_tokens.append("FINALLY")
        
        self.generic_visit(node)
    
    def visit_ExceptHandler(self, node):
        """Visit exception handlers."""
        if node.type:
            self._process_exception_type(node.type)
        else:
            self.structure_tokens.append("EXCEPT_ALL")
        
        if node.name:
            self.structure_tokens.append(f"EXCEPT_AS:{node.name}")
        
        self.generic_visit(node)
    
    def visit_Break(self, node):
        """Visit break statements."""
        self.structure_tokens.append("BREAK")
        self.generic_visit(node)
    
    def visit_Continue(self, node):
        """Visit continue statements."""
        self.structure_tokens.append("CONTINUE")
        self.generic_visit(node)
    
    def visit_Pass(self, node):
        """Visit pass statements."""
        self.structure_tokens.append("PASS")
        self.generic_visit(node)
    
    def visit_Raise(self, node):
        """Visit raise statements."""
        self.structure_tokens.append("RAISE")
        if node.exc:
            self._process_raised_exception(node.exc)
        if node.cause:
            self.structure_tokens.append("RAISE_FROM")
        self.generic_visit(node)
    
    def visit_Assert(self, node):
        """Visit assert statements."""
        self.structure_tokens.append("ASSERT")
        if node.msg:
            self.structure_tokens.append("ASSERT_MSG")
        self.generic_visit(node)
    
    def visit_Match(self, node):
        """Visit match statements (Python 3.10+)."""
        self.structure_tokens.append(f"MATCH:{len(node.cases)}")
        self.complexity += len(node.cases)
        self.generic_visit(node)
    
    def _process_condition(self, test):
        """Process condition complexity."""
        if isinstance(test, ast.Compare):
            self.structure_tokens.append(f"CONDITION_CMP:{len(test.ops)}")
        elif isinstance(test, ast.BoolOp):
            op_name = test.op.__class__.__name__
            self.structure_tokens.append(f"CONDITION_BOOL:{op_name}")
        elif isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            self.structure_tokens.append("CONDITION_NOT")
    
    def _process_iteration_target(self, iter_node):
        """Process iteration target patterns."""
        if isinstance(iter_node, ast.Call):
            if isinstance(iter_node.func, ast.Name):
                func_name = iter_node.func.id
                if func_name in {'range', 'enumerate', 'zip'}:
                    self.structure_tokens.append(f"ITER_{func_name.upper()}")
        elif isinstance(iter_node, ast.Name):
            self.structure_tokens.append("ITER_VAR")
        elif isinstance(iter_node, ast.List):
            self.structure_tokens.append("ITER_LIST")
    
    def _process_with_item(self, item):
        """Process a with statement item."""
        if isinstance(item.context_expr, ast.Call):
            if isinstance(item.context_expr.func, ast.Name):
                self.structure_tokens.append(f"WITH_CALL:{item.context_expr.func.id}")
        if item.optional_vars:
            self.structure_tokens.append("WITH_AS")
    
    def _process_exception_handlers(self, handlers):
        """Process exception handlers."""
        self.structure_tokens.append(f"EXCEPT_COUNT:{len(handlers)}")
        specific_count = sum(1 for h in handlers if h.type is not None)
        if specific_count > 0:
            self.structure_tokens.append(f"EXCEPT_SPECIFIC:{specific_count}")
    
    def _process_exception_type(self, exc_type):
        """Process exception type in handler."""
        if isinstance(exc_type, ast.Name):
            self.structure_tokens.append(f"EXCEPT_TYPE:{exc_type.id}")
        elif isinstance(exc_type, ast.Tuple):
            self.structure_tokens.append(f"EXCEPT_MULTI:{len(exc_type.elts)}")
    
    def _process_raised_exception(self, exc):
        """Process raised exception."""
        if isinstance(exc, ast.Name):
            self.structure_tokens.append(f"RAISE_TYPE:{exc.id}")
        elif isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
            self.structure_tokens.append(f"RAISE_CALL:{exc.func.id}")