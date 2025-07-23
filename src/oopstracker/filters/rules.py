"""
Filtering rules for trivial patterns.
"""

import ast
from typing import Dict, Any
from .config import TrivialFilterConfig


class TrivialFilterRules:
    """Encapsulates all filtering rules for trivial patterns."""
    
    def __init__(self, config: TrivialFilterConfig):
        self.config = config
    
    def is_single_return_function(self, analysis: dict) -> bool:
        """Check if function only contains a single return statement."""
        if not self.config.enable_single_return_filter:
            return False
            
        return (
            analysis.get('statement_count', 0) == 1 and
            analysis.get('has_return', False) and
            not analysis.get('has_loops', False) and
            not analysis.get('has_conditionals', False) and
            not analysis.get('has_try_except', False) and
            analysis.get('is_single_expression', False) and
            analysis.get('max_depth', 0) <= 2
        )
    
    def is_simple_special_method(self, analysis: dict) -> bool:
        """Check if this is a simple special method implementation."""
        if not self.config.enable_simple_special_method_filter:
            return False
            
        name = analysis.get('name', '')
        if name not in self.config.special_methods:
            return False
            
        # Simple __init__ that only assigns attributes
        if name == '__init__' and analysis.get('assigned_attributes'):
            return (
                not analysis.get('has_loops', False) and
                not analysis.get('has_conditionals', False) and
                not analysis.get('has_try_except', False) and
                analysis.get('max_depth', 0) <= 3
            )
        
        # Other special methods with minimal logic
        return (
            analysis.get('statement_count', 0) <= 2 and
            analysis.get('max_depth', 0) <= 3
        )
    
    def is_simple_property(self, analysis: dict) -> bool:
        """Check if this is a simple property getter/setter."""
        if not self.config.enable_simple_property_filter:
            return False
            
        # Check decorators
        decorators = analysis.get('decorator_names', [])
        if 'property' not in decorators and not any('setter' in d for d in decorators):
            return False
            
        # Property getter
        if 'property' in decorators:
            return (
                analysis.get('is_property_getter', False) or
                (analysis.get('statement_count', 0) == 1 and
                 analysis.get('has_return', False))
            )
        
        # Property setter
        return analysis.get('statement_count', 0) <= 2
    
    def is_short_function(self, analysis: dict) -> bool:
        """Check if function is too short to be meaningful."""
        if not self.config.enable_short_function_filter:
            return False
            
        return analysis.get('line_count', 0) <= self.config.max_trivial_lines
    
    def is_simple_converter(self, analysis: dict) -> bool:
        """Check if this is a simple converter method."""
        if not self.config.enable_simple_converter_filter:
            return False
            
        name = analysis.get('name', '')
        return (
            name in self.config.converter_methods and
            analysis.get('statement_count', 0) <= 3 and
            not analysis.get('has_loops', False)
        )
    
    def is_trivial_class(self, analysis: dict) -> bool:
        """Check if this is a trivial class definition."""
        if not self.config.enable_trivial_class_filter:
            return False
            
        # Empty class or class with only pass
        if analysis.get('method_count', 0) == 0:
            return True
        
        # Simple data class
        if analysis.get('has_dataclass_decorator', False):
            return analysis.get('method_count', 0) <= 2
        
        # Exception class with minimal methods
        base_classes = analysis.get('base_classes', [])
        if any('Exception' in base or 'Error' in base for base in base_classes):
            return analysis.get('method_count', 0) <= 2
        
        return False
    
    def is_data_model_class(self, analysis: dict, node: ast.ClassDef) -> bool:
        """Check if this is a data model class (like SQLAlchemy models)."""
        # Check for ORM base classes
        base_classes = analysis.get('base_classes', [])
        orm_indicators = ['Model', 'Base', 'Document', 'Schema']
        
        if any(indicator in base for base in base_classes for indicator in orm_indicators):
            # Check if it mostly contains field definitions
            field_count = 0
            method_count = 0
            
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    # Allow special methods and simple properties
                    if item.name.startswith('__') or any(
                        isinstance(d, ast.Name) and d.id == 'property'
                        for d in item.decorator_list
                    ):
                        continue
                    method_count += 1
                elif isinstance(item, (ast.Assign, ast.AnnAssign)):
                    field_count += 1
            
            # If mostly fields with few methods, it's likely a data model
            return field_count > method_count * 2
        
        return False