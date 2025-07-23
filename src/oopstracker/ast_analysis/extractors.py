"""
Feature extractors for AST analysis.
Each extractor focuses on extracting specific features from AST.
"""

import ast
from typing import List, Set, Dict, Any
from .models import ASTFeatures
from .visitors_v2 import (
    FunctionVisitor, 
    ClassVisitor, 
    ControlFlowVisitor, 
    ExpressionVisitor
)


class StructureExtractor:
    """Extracts structural features from AST."""
    
    def extract(self, tree: ast.AST) -> List[str]:
        """Extract structure tokens from AST."""
        tokens = []
        
        # Extract function information
        func_visitor = FunctionVisitor()
        func_visitor.visit(tree)
        
        for sig in func_visitor.function_signatures:
            tokens.append(f"FUNC:{sig['args_count']}")
            if sig['has_varargs']:
                tokens.append("FUNC:HAS_VARARGS")
            if sig['has_kwargs']:
                tokens.append("FUNC:HAS_KWARGS")
            if sig['decorator_count'] > 0:
                tokens.append(f"DECORATOR:{sig['decorator_count']}")
        
        # Extract class information
        class_visitor = ClassVisitor()
        class_visitor.visit(tree)
        
        for info in class_visitor.class_info:
            tokens.append(f"CLASS:{info['base_count']}")
            tokens.append(f"CLASS_METHODS:{len(info['methods'])}")
            tokens.append(f"CLASS_ATTRS:{len(info['attributes'])}")
        
        return tokens


class ComplexityExtractor:
    """Extracts complexity metrics from AST."""
    
    def extract(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        flow_visitor = ControlFlowVisitor()
        flow_visitor.visit(tree)
        
        # Base complexity
        complexity = 1
        
        # Add complexity for each control structure
        for pattern in flow_visitor.control_patterns:
            if pattern.startswith(('IF:', 'FOR:', 'WHILE:', 'TRY:')):
                complexity += 1
        
        # Add extra complexity for deep nesting
        if flow_visitor.max_nesting > 3:
            complexity += flow_visitor.max_nesting - 3
            
        return complexity


class DependencyExtractor:
    """Extracts dependencies from AST."""
    
    def extract(self, tree: ast.AST) -> Tuple[List[str], List[str]]:
        """Extract imports and function calls."""
        imports = []
        calls = []
        
        # Extract expression information
        expr_visitor = ExpressionVisitor()
        expr_visitor.visit(tree)
        calls = expr_visitor.call_targets
        
        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
                    
        return imports, calls


class TypeExtractor:
    """Extracts type information from AST."""
    
    def extract(self, tree: ast.AST) -> Dict[str, str]:
        """Extract type annotations."""
        func_visitor = FunctionVisitor()
        func_visitor.visit(tree)
        
        types = {}
        types.update(func_visitor.argument_types)
        types.update(func_visitor.return_types)
        
        return types


class UnifiedExtractor:
    """Combines all extractors to produce complete AST features."""
    
    def __init__(self):
        self.structure_extractor = StructureExtractor()
        self.complexity_extractor = ComplexityExtractor()
        self.dependency_extractor = DependencyExtractor()
        self.type_extractor = TypeExtractor()
        
    def extract_features(self, tree: ast.AST) -> ASTFeatures:
        """Extract all features from AST."""
        # Extract structure
        structure_tokens = self.structure_extractor.extract(tree)
        
        # Extract complexity
        complexity = self.complexity_extractor.extract(tree)
        
        # Extract dependencies
        imports, calls = self.dependency_extractor.extract(tree)
        
        # Extract types
        type_annotations = self.type_extractor.extract(tree)
        
        # Extract control flow patterns
        flow_visitor = ControlFlowVisitor()
        flow_visitor.visit(tree)
        control_flow_patterns = flow_visitor.control_patterns
        
        return ASTFeatures(
            structure_tokens=structure_tokens,
            complexity_score=complexity,
            dependencies=imports,
            function_calls=calls,
            imports=imports,
            control_flow_patterns=control_flow_patterns,
            type_annotations=type_annotations
        )