"""
Configuration for trivial pattern filtering.
"""

from dataclasses import dataclass
from typing import Set


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
                
                # Arithmetic methods
                '__add__', '__sub__', '__mul__', '__truediv__', '__floordiv__',
                '__mod__', '__divmod__', '__pow__', '__lshift__', '__rshift__',
                '__and__', '__xor__', '__or__',
                
                # In-place arithmetic methods
                '__iadd__', '__isub__', '__imul__', '__itruediv__', '__ifloordiv__',
                '__imod__', '__ipow__', '__ilshift__', '__irshift__',
                '__iand__', '__ixor__', '__ior__',
                
                # Unary operators
                '__neg__', '__pos__', '__abs__', '__invert__',
                
                # Context managers
                '__enter__', '__exit__',
                
                # Attribute access
                '__getattr__', '__setattr__', '__delattr__', '__getattribute__',
                
                # Descriptors
                '__get__', '__set__', '__delete__', '__set_name__',
                
                # Others
                '__call__', '__copy__', '__deepcopy__', '__getnewargs__',
                '__reduce__', '__reduce_ex__', '__getstate__', '__setstate__',
            }
        
        if self.converter_methods is None:
            self.converter_methods = {
                'to_dict', 'to_json', 'to_string', 'to_str',
                'from_dict', 'from_json', 'from_string', 'from_str',
                'as_dict', 'as_json', 'as_string', 'as_str',
                'serialize', 'deserialize',
                'encode', 'decode',
            }