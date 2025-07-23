"""
Configuration for trivial pattern filtering.
"""

from typing import Set
from dataclasses import dataclass


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
                # Core lifecycle methods
                '__init__', '__new__', '__del__',
                
                # String representation methods
                '__str__', '__repr__', '__format__',
                
                # Comparison methods
                '__eq__', '__ne__', '__lt__', '__le__', '__gt__', '__ge__', '__hash__',
                
                # Type conversion methods
                '__bool__', '__int__', '__float__', '__complex__', '__bytes__',
                
                # Container methods
                '__len__', '__iter__', '__next__', '__reversed__',
                '__getitem__', '__setitem__', '__delitem__', '__contains__',
                
                # Attribute access methods
                '__getattr__', '__setattr__', '__delattr__', '__dir__',
                
                # Context manager methods
                '__enter__', '__exit__',
                
                # Async methods
                '__aenter__', '__aexit__', '__aiter__', '__anext__',
                
                # Descriptor methods
                '__get__', '__set__', '__delete__',
                
                # Copy methods
                '__copy__', '__deepcopy__'
            }
            
        if self.converter_methods is None:
            self.converter_methods = {
                'to_dict', 'to_json', 'to_string', 'to_str',
                'from_dict', 'from_json', 'from_string',
                'as_dict', 'as_json', 'as_string',
                'serialize', 'deserialize',
                'encode', 'decode',
                'parse', 'format'
            }