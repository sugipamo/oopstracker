"""
AST-based code analysis for structural similarity detection.
Extracts semantic structure from code for more accurate duplicate detection.
"""

import ast
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from collections import Counter


logger = logging.getLogger(__name__)


@dataclass
class CodeUnit:
    """Represents a single code unit (function, class, or module)."""
    
    name: str
    type: str  # 'function', 'class', 'module'
    source_code: str
    start_line: int
    end_line: int
    file_path: Optional[str] = None
    
    # AST-derived features
    ast_structure: Optional[str] = None
    complexity_score: Optional[int] = None
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


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


class ASTAnalyzer:
    """
    Analyzes Python code using AST to extract structural information.
    """
    
    def __init__(self):
        self.extractors = {}
    
    def parse_file(self, file_path: str) -> List[CodeUnit]:
        """
        Parse a Python file and extract code units.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of CodeUnit objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            return self.parse_code(source_code, file_path)
        
        except Exception as e:
            print(f"❌ Error parsing file {file_path}: {e}")
            return []
    
    def parse_code(self, source_code: str, file_path: Optional[str] = None) -> List[CodeUnit]:
        """
        Parse Python source code and extract code units.
        
        Args:
            source_code: Python source code
            file_path: Optional file path for context
            
        Returns:
            List of CodeUnit objects
        """
        try:
            tree = ast.parse(source_code)
            units = []
            
            # Extract functions and classes only (skip module-level)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    unit = self._create_function_unit(node, source_code, file_path)
                    units.append(unit)
                elif isinstance(node, ast.ClassDef):
                    unit = self._create_class_unit(node, source_code, file_path)
                    units.append(unit)
            
            return units
        
        except SyntaxError as e:
            logger.debug(f"Syntax error in code: {e}")
            return []
        except Exception as e:
            logger.warning(f"Error parsing code: {e}")
            return []
    
    def _create_module_unit(self, source_code: str, file_path: Optional[str]) -> CodeUnit:
        """Create a code unit for the entire module."""
        extractor = ASTStructureExtractor()
        
        try:
            tree = ast.parse(source_code)
            extractor.visit(tree)
        except:
            pass
        
        return CodeUnit(
            name=Path(file_path).stem if file_path else "module",
            type="module",
            source_code=source_code,
            start_line=1,
            end_line=len(source_code.splitlines()),
            file_path=file_path,
            ast_structure=extractor.get_structure_signature(),
            complexity_score=extractor.complexity,
            dependencies=list(extractor.dependencies)
        )
    
    def _create_function_unit(self, node: ast.FunctionDef, source_code: str, 
                             file_path: Optional[str]) -> CodeUnit:
        """Create a code unit for a function."""
        extractor = ASTStructureExtractor()
        extractor.visit(node)
        
        # Extract function source code
        lines = source_code.splitlines()
        func_lines = lines[node.lineno - 1:node.end_lineno]
        func_source = '\n'.join(func_lines)
        
        return CodeUnit(
            name=node.name,
            type="function",
            source_code=func_source,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            file_path=file_path,
            ast_structure=extractor.get_structure_signature(),
            complexity_score=extractor.complexity,
            dependencies=list(extractor.dependencies)
        )
    
    def _create_class_unit(self, node: ast.ClassDef, source_code: str, 
                          file_path: Optional[str]) -> CodeUnit:
        """Create a code unit for a class."""
        extractor = ASTStructureExtractor()
        extractor.visit(node)
        
        # Extract class source code including decorators
        lines = source_code.splitlines()
        
        # Determine the actual start line (including decorators)
        start_line = node.lineno
        if hasattr(node, 'decorator_list') and node.decorator_list:
            # Use the line number of the first decorator
            start_line = node.decorator_list[0].lineno
        
        class_lines = lines[start_line - 1:node.end_lineno]
        class_source = '\n'.join(class_lines)
        
        return CodeUnit(
            name=node.name,
            type="class",
            source_code=class_source,
            start_line=start_line,
            end_line=node.end_lineno or node.lineno,
            file_path=file_path,
            ast_structure=extractor.get_structure_signature(),
            complexity_score=extractor.complexity,
            dependencies=list(extractor.dependencies)
        )
    
    def calculate_structural_similarity(self, unit1: CodeUnit, unit2: CodeUnit) -> float:
        """
        Calculate structural similarity between two code units using Bag of Words.
        
        Args:
            unit1: First code unit
            unit2: Second code unit
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not unit1.ast_structure or not unit2.ast_structure:
            return 0.0
        
        # Split structure signatures into tokens and count occurrences
        tokens1 = Counter(unit1.ast_structure.split('|'))
        tokens2 = Counter(unit2.ast_structure.split('|'))
        
        # Calculate cosine similarity with frequency
        intersection = sum((tokens1 & tokens2).values())
        magnitude1 = sum(v * v for v in tokens1.values()) ** 0.5
        magnitude2 = sum(v * v for v in tokens2.values()) ** 0.5
        
        if magnitude1 * magnitude2 == 0:
            return 0.0
        
        return intersection / (magnitude1 * magnitude2)
    
    def find_similar_units(self, target_unit: CodeUnit, candidate_units: List[CodeUnit], 
                          threshold: float = 0.7) -> List[Tuple[CodeUnit, float]]:
        """
        Find similar code units based on structural similarity.
        
        Args:
            target_unit: Target code unit to find similarities for
            candidate_units: List of candidate units to compare against
            threshold: Minimum similarity threshold
            
        Returns:
            List of (unit, similarity_score) tuples
        """
        similar_units = []
        
        for candidate in candidate_units:
            if candidate.name == target_unit.name and candidate.file_path == target_unit.file_path:
                continue  # Skip self
            
            similarity = self.calculate_structural_similarity(target_unit, candidate)
            
            if similarity >= threshold:
                similar_units.append((candidate, similarity))
        
        # Sort by similarity score (descending)
        similar_units.sort(key=lambda x: x[1], reverse=True)
        
        return similar_units
    
    def generate_ast_simhash(self, code_unit: CodeUnit) -> int:
        """
        Generate SimHash based on AST structure.
        
        Args:
            code_unit: Code unit to generate hash for
            
        Returns:
            64-bit SimHash value
        """
        if not code_unit.ast_structure:
            return 0
        
        # Use AST structure for SimHash generation
        structure_text = code_unit.ast_structure
        
        # Create weighted features
        features = []
        for token in structure_text.split('|'):
            if token.strip():
                features.append(token.strip())
        
        return self._simhash_from_features(features)
    
    def _simhash_from_features(self, features: List[str]) -> int:
        """
        Generate SimHash from a list of features.
        
        Args:
            features: List of feature strings
            
        Returns:
            64-bit SimHash value
        """
        # Initialize vector
        vector = [0] * 64
        
        for feature in features:
            # Get hash for this feature
            hash_value = int(hashlib.md5(feature.encode()).hexdigest(), 16)
            
            # Update vector based on hash bits
            for i in range(64):
                if hash_value & (1 << i):
                    vector[i] += 1
                else:
                    vector[i] -= 1
        
        # Convert to final hash
        simhash = 0
        for i in range(64):
            if vector[i] > 0:
                simhash |= (1 << i)
        
        return simhash