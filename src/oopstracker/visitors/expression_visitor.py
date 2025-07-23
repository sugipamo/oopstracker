"""Visitor for expression-related AST nodes."""
import ast
from .base import BaseStructureVisitor


class ExpressionVisitor(BaseStructureVisitor):
    """
    Specializes in extracting expression-related structural information.
    Handles operators, comparisons, assignments, and other expressions.
    """
    
    def visit_BinOp(self, node):
        """Visit binary operations."""
        op_name = node.op.__class__.__name__
        self.structure_tokens.append(f"BINOP:{op_name}")
        
        # Add operand types for better matching
        left_type = self._get_node_type(node.left)
        right_type = self._get_node_type(node.right)
        self.structure_tokens.append(f"BINOP_TYPES:{left_type}_{op_name}_{right_type}")
        
        self.generic_visit(node)
    
    def visit_UnaryOp(self, node):
        """Visit unary operations."""
        op_name = node.op.__class__.__name__
        self.structure_tokens.append(f"UNARY:{op_name}")
        self.generic_visit(node)
    
    def visit_Compare(self, node):
        """Visit comparison operations."""
        for op in node.ops:
            op_name = op.__class__.__name__
            self.structure_tokens.append(f"CMP:{op_name}")
        
        # Track comparison chain length
        if len(node.ops) > 1:
            self.structure_tokens.append(f"CMP_CHAIN:{len(node.ops)}")
        
        self.generic_visit(node)
    
    def visit_BoolOp(self, node):
        """Visit boolean operations."""
        op_name = node.op.__class__.__name__
        self.structure_tokens.append(f"BOOL:{op_name}")
        self.structure_tokens.append(f"BOOL_VALUES:{len(node.values)}")
        self.generic_visit(node)
    
    def visit_Assign(self, node):
        """Visit assignment statements."""
        # Track assignment patterns
        self._process_assignment_targets(node.targets)
        self._process_assignment_value(node.value)
        
        self.generic_visit(node)
    
    def visit_AugAssign(self, node):
        """Visit augmented assignment (+=, -=, etc.)."""
        op_name = node.op.__class__.__name__
        self.structure_tokens.append(f"AUGASSIGN:{op_name}")
        
        if isinstance(node.target, ast.Name):
            self.structure_tokens.append(f"AUGASSIGN_VAR:{node.target.id}")
        
        self.generic_visit(node)
    
    def visit_AnnAssign(self, node):
        """Visit annotated assignment (type hints)."""
        self.structure_tokens.append("ANN_ASSIGN")
        
        # Process annotation
        if node.annotation:
            ann_type = self._get_type_name(node.annotation)
            self.structure_tokens.append(f"ANN_TYPE:{ann_type}")
        
        # Process target
        if isinstance(node.target, ast.Name):
            self.structure_tokens.append(f"ANN_VAR:{node.target.id}")
        
        self.generic_visit(node)
    
    def visit_NamedExpr(self, node):
        """Visit named expressions (walrus operator :=)."""
        self.structure_tokens.append("NAMED_EXPR")
        if isinstance(node.target, ast.Name):
            self.structure_tokens.append(f"WALRUS_VAR:{node.target.id}")
        self.generic_visit(node)
    
    def visit_ListComp(self, node):
        """Visit list comprehensions."""
        self.structure_tokens.append(f"LISTCOMP:{len(node.generators)}")
        self._process_comprehension_generators(node.generators)
        self.generic_visit(node)
    
    def visit_DictComp(self, node):
        """Visit dict comprehensions."""
        self.structure_tokens.append(f"DICTCOMP:{len(node.generators)}")
        self._process_comprehension_generators(node.generators)
        self.generic_visit(node)
    
    def visit_SetComp(self, node):
        """Visit set comprehensions."""
        self.structure_tokens.append(f"SETCOMP:{len(node.generators)}")
        self._process_comprehension_generators(node.generators)
        self.generic_visit(node)
    
    def visit_GeneratorExp(self, node):
        """Visit generator expressions."""
        self.structure_tokens.append(f"GENEXP:{len(node.generators)}")
        self._process_comprehension_generators(node.generators)
        self.generic_visit(node)
    
    def visit_IfExp(self, node):
        """Visit conditional expressions (ternary operator)."""
        self.structure_tokens.append("IFEXP")
        self.generic_visit(node)
    
    def visit_Subscript(self, node):
        """Visit subscript operations (indexing/slicing)."""
        self.structure_tokens.append("SUBSCRIPT")
        
        # Check for slice vs index
        if isinstance(node.slice, ast.Slice):
            self.structure_tokens.append("SLICE")
        else:
            self.structure_tokens.append("INDEX")
        
        self.generic_visit(node)
    
    def visit_Import(self, node):
        """Visit import statements."""
        self.structure_tokens.append(f"IMPORT:{len(node.names)}")
        for alias in node.names:
            self.imports.append(alias.name)
            if alias.asname:
                self.structure_tokens.append(f"IMPORT_AS:{alias.asname}")
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Visit from-import statements."""
        module = node.module or ""
        self.structure_tokens.append(f"FROM_IMPORT:{module}")
        self.structure_tokens.append(f"IMPORT_NAMES:{len(node.names)}")
        
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}" if module else alias.name)
            if alias.asname:
                self.structure_tokens.append(f"IMPORT_AS:{alias.asname}")
        
        self.generic_visit(node)
    
    def _process_assignment_targets(self, targets):
        """Process assignment targets."""
        for target in targets:
            if isinstance(target, ast.Name):
                # Track variable assignment with potential type
                self.structure_tokens.append(f"ASSIGN_VAR:{target.id}")
            elif isinstance(target, (ast.Tuple, ast.List)):
                # Track unpacking assignments
                self.structure_tokens.append(f"UNPACK:{len(target.elts)}")
            elif isinstance(target, ast.Subscript):
                self.structure_tokens.append("ASSIGN_SUBSCRIPT")
            elif isinstance(target, ast.Attribute):
                self.structure_tokens.append("ASSIGN_ATTR")
    
    def _process_assignment_value(self, value):
        """Process assignment value."""
        value_type = self._infer_value_type(value)
        self.structure_tokens.append(f"ASSIGN_VALUE:{value_type}")
    
    def _process_comprehension_generators(self, generators):
        """Process comprehension generators."""
        for gen in generators:
            # Track iteration target
            if isinstance(gen.iter, ast.Name):
                self.structure_tokens.append("COMP_ITER_VAR")
            elif isinstance(gen.iter, ast.Call):
                if isinstance(gen.iter.func, ast.Name):
                    self.structure_tokens.append(f"COMP_ITER_CALL:{gen.iter.func.id}")
            
            # Track filters
            if gen.ifs:
                self.structure_tokens.append(f"COMP_FILTERS:{len(gen.ifs)}")