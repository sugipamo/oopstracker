"""
Code structure analysis and statistics.
"""

import ast
import logging
from typing import Dict, List, Optional, Set

from ...ast_analyzer import ASTAnalyzer, CodeUnit
from ...models import CodeRecord
from ..simhash import SimHashCalculator

logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """
    Analyzes code structure and provides statistics.
    """
    
    def __init__(self, analyzer: ASTAnalyzer, simhash_calculator: SimHashCalculator):
        """
        Initialize code analyzer.
        
        Args:
            analyzer: AST analyzer instance
            simhash_calculator: SimHash calculator for accessing stored records
        """
        self.analyzer = analyzer
        self.simhash_calculator = simhash_calculator
        
    def analyze_code_structure(self, source_code: str, file_path: Optional[str] = None) -> Dict:
        """
        Analyze code structure without registering.
        
        Args:
            source_code: Python source code
            file_path: Optional file path for context
            
        Returns:
            Dictionary with analysis results
        """
        units = self.analyzer.parse_code(source_code, file_path or "")
        
        analysis = {
            "total_units": len(units),
            "functions": [self._unit_to_dict(u) for u in units if u.type == "function"],
            "classes": [self._unit_to_dict(u) for u in units if u.type == "class"],
            "methods": [self._unit_to_dict(u) for u in units if u.type == "method"]
        }
        
        # Add complexity analysis
        total_complexity = sum(u.complexity_score or 0 for u in units)
        analysis["total_complexity"] = total_complexity
        analysis["average_complexity"] = total_complexity / len(units) if units else 0
        
        # Add dependency analysis
        all_deps: Set[str] = set()
        for unit in units:
            all_deps.update(unit.dependencies or [])
        analysis["dependencies"] = sorted(all_deps)
        
        # Add size metrics
        analysis["total_lines"] = sum(u.line_count or 0 for u in units)
        analysis["largest_unit"] = max((u.line_count or 0 for u in units), default=0)
        
        return analysis
        
    def _unit_to_dict(self, unit: CodeUnit) -> Dict:
        """Convert a code unit to a dictionary for analysis results."""
        return {
            "name": unit.name,
            "type": unit.type,
            "line_number": unit.line_number,
            "line_count": unit.line_count,
            "complexity": unit.complexity_score,
            "dependencies": list(unit.dependencies or [])
        }
        
    def get_statistics(self) -> Dict:
        """
        Get detector statistics.
        
        Returns:
            Dictionary with statistics
        """
        records = self.simhash_calculator.get_all_records()
        
        # Count by type
        function_count = sum(1 for r in records if r.function_name and not r.function_name.startswith("class "))
        class_count = sum(1 for r in records if r.function_name and r.function_name.startswith("class "))
        
        # File statistics
        unique_files = {r.full_path for r in records}
        
        # Size statistics
        total_lines = sum(r.source_code.count('\n') + 1 for r in records)
        avg_lines = total_lines / len(records) if records else 0
        
        # Complexity distribution
        complexity_buckets = {"low": 0, "medium": 0, "high": 0, "very_high": 0}
        
        for record in records:
            unit = self.simhash_calculator.get_code_unit(record.code_hash)
            if unit and unit.complexity_score:
                if unit.complexity_score < 5:
                    complexity_buckets["low"] += 1
                elif unit.complexity_score < 10:
                    complexity_buckets["medium"] += 1
                elif unit.complexity_score < 20:
                    complexity_buckets["high"] += 1
                else:
                    complexity_buckets["very_high"] += 1
        
        return {
            "total_records": len(records),
            "total_units": len(self.simhash_calculator.code_units),
            "function_count": function_count,
            "class_count": class_count,
            "unique_files": len(unique_files),
            "total_lines": total_lines,
            "average_lines_per_unit": avg_lines,
            "complexity_distribution": complexity_buckets,
            "hamming_threshold": self.simhash_calculator.hamming_threshold
        }
        
    def get_file_statistics(self, file_path: str) -> Optional[Dict]:
        """
        Get statistics for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file statistics or None if file not found
        """
        file_records = [
            r for r in self.simhash_calculator.get_all_records()
            if r.full_path == file_path
        ]
        
        if not file_records:
            return None
            
        file_units = []
        for record in file_records:
            unit = self.simhash_calculator.get_code_unit(record.code_hash)
            if unit:
                file_units.append(unit)
                
        return {
            "file_path": file_path,
            "total_units": len(file_units),
            "functions": sum(1 for u in file_units if u.type == "function"),
            "classes": sum(1 for u in file_units if u.type == "class"),
            "methods": sum(1 for u in file_units if u.type == "method"),
            "total_lines": sum(u.line_count or 0 for u in file_units),
            "total_complexity": sum(u.complexity_score or 0 for u in file_units),
            "average_complexity": sum(u.complexity_score or 0 for u in file_units) / len(file_units) if file_units else 0
        }
        
    def get_complexity_report(self, threshold: int = 10) -> List[Dict]:
        """
        Get report of high-complexity code units.
        
        Args:
            threshold: Minimum complexity score to include
            
        Returns:
            List of high-complexity units sorted by complexity
        """
        high_complexity = []
        
        for record in self.simhash_calculator.get_all_records():
            unit = self.simhash_calculator.get_code_unit(record.code_hash)
            if unit and unit.complexity_score and unit.complexity_score >= threshold:
                high_complexity.append({
                    "name": unit.name,
                    "file": unit.file_path,
                    "line": unit.line_number,
                    "type": unit.type,
                    "complexity": unit.complexity_score,
                    "lines": unit.line_count
                })
                
        # Sort by complexity descending
        high_complexity.sort(key=lambda x: x["complexity"], reverse=True)
        
        return high_complexity
    
    def analyze(self, source_code: str) -> Dict:
        """
        Analyze code and return comprehensive analysis results.
        
        Args:
            source_code: Python source code to analyze
            
        Returns:
            Dictionary with ast, metrics, features, and possibly error
        """
        result = {
            "ast": None,
            "metrics": {},
            "features": {},
            "error": None
        }
        
        # Try to parse AST
        try:
            tree = ast.parse(source_code)
            result["ast"] = tree
        except SyntaxError as e:
            result["error"] = str(e)
            return result
        
        # Use existing ASTAnalyzer to extract code units
        units = self.analyzer.parse_code(source_code)
        
        # Extract features
        features = {
            "functions": [],
            "classes": [],
            "methods": [],
            "imports": [],
            "variables": [],
            "decorators": [],
            "control_flow": []
        }
        
        # Extract features from code units
        for unit in units:
            if unit.type == "function":
                features["functions"].append(unit.name)
            elif unit.type == "class":
                features["classes"].append(unit.name)
            elif unit.type == "method":
                features["methods"].append(unit.name)
        
        # Extract methods from classes
        class MethodExtractor(ast.NodeVisitor):
            def __init__(self):
                self.methods = []
                self.in_class = False
                
            def visit_ClassDef(self, node):
                old_in_class = self.in_class
                self.in_class = True
                self.generic_visit(node)
                self.in_class = old_in_class
                
            def visit_FunctionDef(self, node):
                if self.in_class:
                    self.methods.append(node.name)
                self.generic_visit(node)
                
            def visit_AsyncFunctionDef(self, node):
                if self.in_class:
                    self.methods.append(node.name)
                self.generic_visit(node)
        
        method_extractor = MethodExtractor()
        method_extractor.visit(tree)
        features["methods"] = method_extractor.methods
        
        # Extract additional features from AST
        class FeatureVisitor(ast.NodeVisitor):
            def __init__(self):
                self.imports = []
                self.variables = []
                self.decorators = []
                self.control_flow = []
                self.in_function = False
                self.max_nesting = 0
                self.current_nesting = 0
                
            def visit_Import(self, node):
                for alias in node.names:
                    self.imports.append(alias.name.split('.')[0])
                self.generic_visit(node)
                    
            def visit_ImportFrom(self, node):
                if node.module:
                    self.imports.append(node.module.split('.')[0])
                self.generic_visit(node)
                    
            def visit_Assign(self, node):
                for target in node.targets:
                    if isinstance(target, ast.Name) and not self.in_function:
                        self.variables.append(target.id)
                self.generic_visit(node)
                
            def visit_FunctionDef(self, node):
                old_in_function = self.in_function
                self.in_function = True
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        self.decorators.append(decorator.id)
                    elif isinstance(decorator, ast.Attribute):
                        self.decorators.append(decorator.attr)
                self.current_nesting += 1
                self.max_nesting = max(self.max_nesting, self.current_nesting)
                self.generic_visit(node)
                self.current_nesting -= 1
                self.in_function = old_in_function
                
            def visit_ClassDef(self, node):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        self.decorators.append(decorator.id)
                    elif isinstance(decorator, ast.Attribute):
                        self.decorators.append(decorator.attr)
                self.current_nesting += 1
                self.max_nesting = max(self.max_nesting, self.current_nesting)
                self.generic_visit(node)
                self.current_nesting -= 1
                    
            def visit_For(self, node):
                self.control_flow.append("for")
                self.generic_visit(node)
                
            def visit_While(self, node):
                self.control_flow.append("while")
                self.generic_visit(node)
                
            def visit_If(self, node):
                self.control_flow.append("if")
                self.generic_visit(node)
                
            def visit_Try(self, node):
                self.control_flow.append("try")
                self.generic_visit(node)
        
        visitor = FeatureVisitor()
        visitor.visit(tree)
        
        # Update features
        features["imports"] = visitor.imports
        features["variables"] = visitor.variables
        features["decorators"] = visitor.decorators
        features["control_flow"] = visitor.control_flow
        
        result["features"] = features
        
        # Calculate metrics
        lines = source_code.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Calculate cyclomatic complexity
        complexity = 1  # Base complexity
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        
        result["metrics"] = {
            "loc": len(non_empty_lines),
            "complexity": complexity,
            "nesting_depth": visitor.max_nesting
        }
        
        return result
    
    def extract_features(self, source_code: str) -> List[str]:
        """
        Extract features from code for similarity comparison.
        
        Args:
            source_code: Python source code
            
        Returns:
            List of feature strings
        """
        features = []
        
        # Use ASTAnalyzer to extract code units
        units = self.analyzer.parse_code(source_code)
        
        # Extract features from code units
        for unit in units:
            if unit.type == "function":
                features.append(f"func:{unit.name}")
            elif unit.type == "class":
                features.append(f"class:{unit.name}")
            
            # Add structural features from unit
            if unit.ast_structure:
                features.extend(unit.ast_structure.split("|"))
        
        # Parse AST for additional features
        try:
            tree = ast.parse(source_code)
            
            # Count function arguments
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    features.append(f"args:{len(node.args.args)}")
                elif isinstance(node, ast.Return):
                    features.append("return")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        features.append(f"import:{alias.name}")
        except SyntaxError:
            logger.debug("Syntax error during feature extraction")
        
        return features
    
    def get_feature_weights(self, features: List[str], analysis_result: Dict) -> List[int]:
        """
        Calculate weights for features based on their importance.
        
        Args:
            features: List of feature strings
            analysis_result: Result from analyze() method
            
        Returns:
            List of weights corresponding to features
        """
        weights = []
        
        for feature in features:
            weight = 1  # Default weight
            
            # Give higher weight to structural elements
            if feature.startswith('class:'):
                weight = 3
            elif feature.startswith('func:'):
                weight = 2
            elif feature.startswith('import:'):
                weight = 1
            elif feature in ['return', 'if', 'for', 'while']:
                weight = 1
            
            weights.append(weight)
        
        return weights
    
    def normalize_code(self, source_code: str) -> str:
        """
        Normalize code by removing extra whitespace and formatting consistently.
        
        Args:
            source_code: Python source code
            
        Returns:
            Normalized code string
        """
        # Parse and unparse to normalize formatting
        try:
            tree = ast.parse(source_code)
            # Convert back to code (note: this removes comments)
            normalized = ast.unparse(tree)
            return normalized
        except (SyntaxError, AttributeError):
            # If parsing fails or unparse is not available (Python < 3.9)
            # Just do basic normalization
            lines = source_code.split('\n')
            normalized_lines = []
            for line in lines:
                # Remove trailing whitespace
                line = line.rstrip()
                # Skip empty lines
                if line:
                    normalized_lines.append(line)
            return '\n'.join(normalized_lines)