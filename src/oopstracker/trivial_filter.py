"""
Trivial code pattern filter for OOPStracker.
Filters out common, acceptable patterns that appear as duplicates but are actually appropriate.
"""

import ast
from typing import List, Set, Optional
from dataclasses import dataclass
from .models import CodeRecord


@dataclass
class TrivialFilterConfig:
    """Configuration for trivial pattern filtering."""
    
    # Level 1 filters (always applied)
    enable_single_return_filter: bool = True
    enable_simple_special_method_filter: bool = True
    enable_trivial_class_filter: bool = True
    enable_simple_property_filter: bool = True
    
    # Level 2 filters (configurable)
    enable_short_function_filter: bool = False
    max_trivial_lines: int = 3
    enable_simple_converter_filter: bool = False
    
    # Special method names that are commonly trivial
    special_methods: Set[str] = None
    
    # Converter method names that are often trivial
    converter_methods: Set[str] = None
    
    def __post_init__(self):
        if self.special_methods is None:
            self.special_methods = {
                '__str__', '__repr__', '__eq__', '__hash__', '__bool__',
                '__len__', '__iter__', '__next__', '__getitem__', '__setitem__',
                '__contains__', '__enter__', '__exit__'
            }
        
        if self.converter_methods is None:
            self.converter_methods = {
                'to_dict', 'to_json', 'to_yaml', 'to_xml', 'to_string',
                'to_summary', 'to_list', 'to_tuple', 'to_set',
                'serialize', 'deserialize'
            }


class TrivialPatternAnalyzer(ast.NodeVisitor):
    """
    Analyzes AST nodes to identify trivial patterns that should be excluded from duplication detection.
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset analyzer state."""
        self.return_count = 0
        self.statement_count = 0
        self.has_single_return = False
        self.return_expressions = []
        self.is_pass_only = False
        self.docstring_lines = 0
        self.actual_code_lines = 0
        
    def visit_Return(self, node):
        """Count return statements and analyze their content."""
        self.return_count += 1
        
        if node.value:
            # Analyze return expression
            if isinstance(node.value, ast.Name):
                # return self.property, return variable
                self.return_expressions.append(f"name:{node.value.id}")
            elif isinstance(node.value, ast.Attribute):
                # return self.field, return obj.attr
                self.return_expressions.append(f"attr:{node.value.attr}")
            elif isinstance(node.value, ast.Constant):
                # return "constant", return 42
                self.return_expressions.append(f"const:{type(node.value.value).__name__}")
            else:
                # More complex expression
                self.return_expressions.append("complex")
        else:
            # return without value
            self.return_expressions.append("none")
        
        self.generic_visit(node)
    
    def visit_Pass(self, node):
        """Check for pass-only functions/classes."""
        self.is_pass_only = True
        self.generic_visit(node)
    
    def visit_Expr(self, node):
        """Count expression statements (including docstrings)."""
        # Check if this is a docstring
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            # This is likely a docstring - count it but don't add to statement count
            self.docstring_lines += len(node.value.value.splitlines())
        else:
            self.statement_count += 1
        
        self.generic_visit(node)
    
    def visit_Assign(self, node):
        """Count assignment statements."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def visit_AugAssign(self, node):
        """Count augmented assignment statements."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def visit_If(self, node):
        """Count if statements."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def visit_For(self, node):
        """Count for loops."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def visit_While(self, node):
        """Count while loops."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def visit_Try(self, node):
        """Count try blocks."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def visit_With(self, node):
        """Count with statements."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def visit_Raise(self, node):
        """Count raise statements."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def visit_Assert(self, node):
        """Count assert statements."""
        self.statement_count += 1
        self.generic_visit(node)
    
    def analyze_function(self, node: ast.FunctionDef) -> dict:
        """
        Analyze a function node for trivial patterns.
        
        Returns:
            Dictionary with analysis results
        """
        self.reset()
        self.visit(node)
        
        # Calculate actual code lines (excluding docstring and decorators)
        total_lines = (node.end_lineno or node.lineno) - node.lineno + 1
        
        # Subtract docstring lines from total
        # For actual code complexity, we focus on executable statements
        if self.docstring_lines > 0:
            # Docstring takes up lines, but we want to measure code complexity
            self.actual_code_lines = total_lines - min(self.docstring_lines, total_lines - 2)
        else:
            self.actual_code_lines = total_lines
        
        # For trivial detection, we care more about the statement count
        return {
            'name': node.name,
            'is_special_method': node.name.startswith('__') and node.name.endswith('__'),
            'return_count': self.return_count,
            'statement_count': self.statement_count,
            'has_single_return': self.return_count == 1,
            'return_expressions': self.return_expressions,
            'is_pass_only': self.is_pass_only,
            'total_lines': total_lines,
            'actual_code_lines': self.actual_code_lines,
            'docstring_lines': self.docstring_lines,
            'has_decorator': len(node.decorator_list) > 0,
            'arg_count': len(node.args.args)
        }
    
    def analyze_class(self, node: ast.ClassDef) -> dict:
        """
        Analyze a class node for trivial patterns.
        
        Returns:
            Dictionary with analysis results
        """
        self.reset()
        self.visit(node)
        
        # Count methods and attributes
        method_count = 0
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                method_count += 1
        
        # Calculate actual code lines
        total_lines = (node.end_lineno or node.lineno) - node.lineno + 1
        self.actual_code_lines = total_lines - self.docstring_lines
        
        return {
            'name': node.name,
            'method_count': method_count,
            'base_count': len(node.bases),
            'statement_count': self.statement_count,
            'is_pass_only': self.is_pass_only,
            'total_lines': total_lines,
            'actual_code_lines': self.actual_code_lines,
            'docstring_lines': self.docstring_lines,
            'has_decorator': len(node.decorator_list) > 0
        }


class TrivialPatternFilter:
    """
    Filters out trivial code patterns that are commonly duplicated but acceptable.
    """
    
    def __init__(self, config: Optional[TrivialFilterConfig] = None):
        self.config = config or TrivialFilterConfig()
        self.analyzer = TrivialPatternAnalyzer()
    
    def should_exclude_code_record(self, record: CodeRecord) -> bool:
        """
        Determine if a code record should be excluded from duplication detection.
        
        Args:
            record: Code record to analyze
            
        Returns:
            True if the record should be excluded
        """
        if not record.code_content:
            return True
        
        try:
            tree = ast.parse(record.code_content)
            
            # Find the main function or class
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if self._should_exclude_function(node):
                        return True
                elif isinstance(node, ast.ClassDef):
                    if self._should_exclude_class(node):
                        return True
            
            return False
            
        except (SyntaxError, ValueError):
            # If we can't parse it, don't exclude it
            return False
    
    def _should_exclude_function(self, node: ast.FunctionDef) -> bool:
        """Check if a function should be excluded."""
        analysis = self.analyzer.analyze_function(node)
        
        # Level 1 filters (always applied)
        if self.config.enable_single_return_filter:
            if self._is_single_return_function(analysis):
                return True
        
        if self.config.enable_simple_special_method_filter:
            if self._is_simple_special_method(analysis):
                return True
        
        if self.config.enable_simple_property_filter:
            if self._is_simple_property(analysis):
                return True
        
        # Level 2 filters (configurable)
        if self.config.enable_short_function_filter:
            if self._is_short_function(analysis):
                return True
        
        if self.config.enable_simple_converter_filter:
            if self._is_simple_converter(analysis):
                return True
        
        return False
    
    def _should_exclude_class(self, node: ast.ClassDef) -> bool:
        """Check if a class should be excluded."""
        analysis = self.analyzer.analyze_class(node)
        
        if self.config.enable_trivial_class_filter:
            if self._is_trivial_class(analysis):
                return True
            
            # Check for Pydantic models and dataclasses
            if self._is_data_model_class(analysis, node):
                return True
        
        return False
    
    def _is_single_return_function(self, analysis: dict) -> bool:
        """Check if function has only a single return statement."""
        if not analysis['has_single_return']:
            return False
        
        # The function should have only a return statement (no other statements)
        # statement_count should be 0 (return is not counted as a statement in our logic)
        if analysis['statement_count'] > 0:
            return False
        
        # Check return expression type
        if not analysis['return_expressions']:
            return True  # return with no value
        
        expr = analysis['return_expressions'][0]
        # Accept simple attribute access (self.prop, self._prop) and constants
        return (
            expr.startswith('attr:') or 
            expr.startswith('name:') or
            expr.startswith('const:')
        )
    
    def _is_simple_special_method(self, analysis: dict) -> bool:
        """Check if this is a simple special method."""
        return (
            analysis['is_special_method'] and 
            analysis['name'] in self.config.special_methods and
            analysis['statement_count'] <= 1
        )
    
    def _is_simple_property(self, analysis: dict) -> bool:
        """Check if this is a simple property getter/setter."""
        return (
            analysis['has_decorator'] and
            analysis['has_single_return'] and
            analysis['statement_count'] <= 0 and
            analysis['return_expressions'] and
            analysis['return_expressions'][0].startswith('attr:')
        )
    
    def _is_short_function(self, analysis: dict) -> bool:
        """Check if function is very short (configurable)."""
        return (
            analysis['statement_count'] <= 1
        )
    
    def _is_simple_converter(self, analysis: dict) -> bool:
        """Check if this is a simple converter method."""
        return (
            analysis['name'] in self.config.converter_methods and
            analysis['statement_count'] <= 3
        )
    
    def _is_trivial_class(self, analysis: dict) -> bool:
        """Check if class is trivial."""
        return (
            analysis['is_pass_only'] or
            (analysis['method_count'] == 0 and analysis['statement_count'] == 0) or
            (analysis['method_count'] <= 1 and analysis['statement_count'] <= 0)
        )
    
    def _is_data_model_class(self, analysis: dict, node: ast.ClassDef) -> bool:
        """Check if class is a data model (Pydantic, dataclass, etc.)."""
        # Check for dataclass decorator
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == 'dataclass':
                return True
            if isinstance(decorator, ast.Attribute) and decorator.attr == 'dataclass':
                return True
        
        # Check for Pydantic BaseModel inheritance
        for base in node.bases:
            if isinstance(base, ast.Name):
                if base.id in ['BaseModel', 'BaseSettings']:
                    return True
            elif isinstance(base, ast.Attribute):
                if base.attr in ['BaseModel', 'BaseSettings']:
                    return True
        
        # Check for TypedDict
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == 'TypedDict':
                return True
            if isinstance(base, ast.Attribute) and base.attr == 'TypedDict':
                return True
        
        # Check for NamedTuple
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == 'NamedTuple':
                return True
            if isinstance(base, ast.Attribute) and base.attr == 'NamedTuple':
                return True
        
        # Check for Enum classes
        for base in node.bases:
            if isinstance(base, ast.Name):
                if base.id in ['Enum', 'IntEnum', 'Flag', 'IntFlag']:
                    return True
            elif isinstance(base, ast.Attribute):
                if base.attr in ['Enum', 'IntEnum', 'Flag', 'IntFlag']:
                    return True
        
        return False
    
    def filter_records(self, records: List[CodeRecord]) -> List[CodeRecord]:
        """
        Filter a list of code records, removing trivial patterns.
        
        Args:
            records: List of code records to filter
            
        Returns:
            Filtered list of code records
        """
        filtered_records = []
        
        for record in records:
            if not self.should_exclude_code_record(record):
                filtered_records.append(record)
        
        return filtered_records
    
    def get_exclusion_stats(self, records: List[CodeRecord]) -> dict:
        """
        Get statistics about what would be excluded.
        
        Args:
            records: List of code records to analyze
            
        Returns:
            Dictionary with exclusion statistics
        """
        total_count = len(records)
        excluded_count = 0
        exclusion_reasons = {
            'single_return': 0,
            'simple_special_method': 0,
            'simple_property': 0,
            'short_function': 0,
            'simple_converter': 0,
            'trivial_class': 0
        }
        
        for record in records:
            if self.should_exclude_code_record(record):
                excluded_count += 1
                # You could add more detailed reason tracking here
        
        return {
            'total_records': total_count,
            'excluded_count': excluded_count,
            'retained_count': total_count - excluded_count,
            'exclusion_percentage': (excluded_count / total_count * 100) if total_count > 0 else 0,
            'exclusion_reasons': exclusion_reasons
        }