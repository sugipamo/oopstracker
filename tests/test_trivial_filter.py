"""
Tests for trivial pattern filtering functionality.
"""

import pytest
from oopstracker.trivial_filter import TrivialPatternFilter, TrivialFilterConfig
from oopstracker.models import CodeRecord


class TestTrivialPatternFilter:
    """Test trivial pattern filtering functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.filter = TrivialPatternFilter()
        self.config = TrivialFilterConfig()
    
    def _assert_should_exclude(self, code: str, function_name: str, expected: bool, description: str = None):
        """Centralized assertion helper for exclusion tests.
        
        Args:
            code: Code content to test
            function_name: Name of the function/class
            expected: Expected exclusion result
            description: Optional description for debugging
        """
        record = CodeRecord(code_content=code, function_name=function_name)
        result = self.filter.should_exclude_code_record(record)
        if description:
            assert result == expected, f"Failed: {description}"
        else:
            assert result == expected
    
    def test_simple_return_functions_excluded(self):
        """Test that simple return functions are excluded."""
        test_cases = [
            ('def get_level(self):\n    return self.level', 'get_level', 'attribute access'),
            ('def get_value(self):\n    return self._value', 'get_value', 'private attribute access'),
            ('def get_default(self):\n    return 42', 'get_default', 'constant return'),
        ]
        
        for code, func_name, description in test_cases:
            self._assert_should_exclude(code, func_name, True, f"Simple return with {description}")
    
    def test_complex_function_not_excluded(self):
        """Test that complex functions are not excluded."""
        code = '''
def process_data(self, data):
    if not data:
        return None
    result = []
    for item in data:
        if item.is_valid():
            result.append(item.process())
    return result
'''
        record = CodeRecord(code_content=code, function_name="process_data")
        assert self.filter.should_exclude_code_record(record) == False
    
    def test_simple_special_method_excluded(self):
        """Test that simple special methods are excluded."""
        code = 'def __str__(self):\n    return self.name'
        self._assert_should_exclude(code, '__str__', True, 'Simple __str__ method')
    
    def test_complex_special_method_not_excluded(self):
        """Test that complex special methods are not excluded."""
        code = '''
def __str__(self):
    parts = []
    if self.name:
        parts.append(f"Name: {self.name}")
    if self.value:
        parts.append(f"Value: {self.value}")
    return " - ".join(parts)
'''
        record = CodeRecord(code_content=code, function_name="__str__")
        assert self.filter.should_exclude_code_record(record) == False
    
    def test_trivial_classes_excluded(self):
        """Test that trivial classes are excluded."""
        test_cases = [
            ('class EmptyClass:\n    pass', 'EmptyClass', 'empty class'),
            ('class DocumentedClass:\n    """This class does nothing."""\n    pass', 'DocumentedClass', 'docstring-only class'),
        ]
        
        for code, class_name, description in test_cases:
            self._assert_should_exclude(code, class_name, True, f"Trivial class: {description}")
    
    def test_functional_class_not_excluded(self):
        """Test that functional classes are not excluded."""
        code = '''
class DataProcessor:
    def __init__(self, data):
        self.data = data
    
    def process(self):
        return [item * 2 for item in self.data]
'''
        record = CodeRecord(code_content=code, function_name="DataProcessor")
        assert self.filter.should_exclude_code_record(record) == False
    
    def test_property_getter_excluded(self):
        """Test that simple property getters are excluded."""
        code = '''
@property
def name(self):
    return self._name
'''
        record = CodeRecord(code_content=code, function_name="name")
        assert self.filter.should_exclude_code_record(record) == True
    
    def test_to_dict_method_behavior(self):
        """Test to_dict method filtering behavior."""
        # Simple to_dict should be excluded when converter filter is enabled
        simple_code = '''
def to_dict(self):
    return {"name": self.name}
'''
        record = CodeRecord(code_content=simple_code, function_name="to_dict")
        
        # Test with converter filter disabled (default)
        filter_disabled = TrivialPatternFilter()
        assert filter_disabled.should_exclude_code_record(record) == False
        
        # Test with converter filter enabled
        config = TrivialFilterConfig(enable_simple_converter_filter=True)
        filter_enabled = TrivialPatternFilter(config)
        assert filter_enabled.should_exclude_code_record(record) == True
    
    def test_complex_to_dict_not_excluded(self):
        """Test that complex to_dict methods are not excluded."""
        code = '''
def to_dict(self):
    result = {}
    for key, value in self.__dict__.items():
        if not key.startswith('_'):
            if hasattr(value, 'to_dict'):
                result[key] = value.to_dict()
            else:
                result[key] = value
    return result
'''
        record = CodeRecord(code_content=code, function_name="to_dict")
        
        config = TrivialFilterConfig(enable_simple_converter_filter=True)
        filter = TrivialPatternFilter(config)
        assert filter.should_exclude_code_record(record) == False
    
    def test_short_function_filter(self):
        """Test configurable short function filter."""
        code = '''
def simple_func(self):
    print("hello")
'''
        record = CodeRecord(code_content=code, function_name="simple_func")
        
        # Test with short function filter disabled (default)
        filter_disabled = TrivialPatternFilter()
        assert filter_disabled.should_exclude_code_record(record) == False
        
        # Test with short function filter enabled
        config = TrivialFilterConfig(enable_short_function_filter=True, max_trivial_lines=2)
        filter_enabled = TrivialPatternFilter(config)
        assert filter_enabled.should_exclude_code_record(record) == True
    
    def test_docstring_ignored_in_line_count(self):
        """Test that docstrings are ignored in line count calculations."""
        code = '''
def documented_getter(self):
    """
    Get the value.
    
    Returns:
        The current value.
    """
    return self.value
'''
        record = CodeRecord(code_content=code, function_name="documented_getter")
        # Should still be excluded despite the docstring
        assert self.filter.should_exclude_code_record(record) == True
    
    def test_multiple_returns_not_excluded(self):
        """Test that functions with multiple returns are not excluded."""
        code = '''
def get_value(self, default=None):
    if self.value is None:
        return default
    return self.value
'''
        record = CodeRecord(code_content=code, function_name="get_value")
        assert self.filter.should_exclude_code_record(record) == False
    
    def test_filter_records_list(self):
        """Test filtering a list of records."""
        records = [
            CodeRecord(code_content="def get_level(self):\n    return self.level", function_name="get_level"),
            CodeRecord(code_content="def complex_func(self):\n    x = 1\n    y = 2\n    return x + y", function_name="complex_func"),
            CodeRecord(code_content="def __str__(self):\n    return self.name", function_name="__str__"),
        ]
        
        filtered = self.filter.filter_records(records)
        # Should exclude the first and third records
        assert len(filtered) == 1
        assert filtered[0].function_name == "complex_func"
    
    def test_exclusion_statistics(self):
        """Test exclusion statistics generation."""
        records = [
            CodeRecord(code_content="def get_level(self):\n    return self.level", function_name="get_level"),
            CodeRecord(code_content="def complex_func(self):\n    x = 1\n    y = 2\n    return x + y", function_name="complex_func"),
            CodeRecord(code_content="def __str__(self):\n    return self.name", function_name="__str__"),
        ]
        
        stats = self.filter.get_exclusion_stats(records)
        
        assert stats['total_records'] == 3
        assert stats['excluded_count'] == 2
        assert stats['retained_count'] == 1
        assert stats['exclusion_percentage'] == pytest.approx(66.67, rel=1e-2)
    
    def test_invalid_code_not_excluded(self):
        """Test that invalid code is not excluded (safe default)."""
        record = CodeRecord(code_content="invalid python syntax !!!", function_name="invalid")
        assert self.filter.should_exclude_code_record(record) == False
    
    def test_empty_code_excluded(self):
        """Test that empty code is excluded."""
        record = CodeRecord(code_content="", function_name="empty")
        assert self.filter.should_exclude_code_record(record) == True
        
        record2 = CodeRecord(code_content=None, function_name="none")
        assert self.filter.should_exclude_code_record(record2) == True
    
    def test_config_special_methods(self):
        """Test custom special method configuration."""
        config = TrivialFilterConfig(
            special_methods={'__custom__', '__special__'},
            enable_single_return_filter=False  # Disable single return filter for this test
        )
        filter = TrivialPatternFilter(config)
        
        code = '''
def __custom__(self):
    return self.value
'''
        record = CodeRecord(code_content=code, function_name="__custom__")
        assert filter.should_exclude_code_record(record) == True
        
        # Standard special method should not be excluded with custom config
        code2 = '''
def __str__(self):
    return self.name
'''
        record2 = CodeRecord(code_content=code2, function_name="__str__")
        assert filter.should_exclude_code_record(record2) == False
    
    def test_config_converter_methods(self):
        """Test custom converter method configuration."""
        config = TrivialFilterConfig(
            enable_simple_converter_filter=True,
            converter_methods={'to_custom', 'serialize_data'}
        )
        filter = TrivialPatternFilter(config)
        
        code = '''
def to_custom(self):
    return {"data": self.data}
'''
        record = CodeRecord(code_content=code, function_name="to_custom")
        assert filter.should_exclude_code_record(record) == True
        
        # Standard converter method should not be excluded with custom config
        code2 = '''
def to_dict(self):
    return {"name": self.name}
'''
        record2 = CodeRecord(code_content=code2, function_name="to_dict")
        assert filter.should_exclude_code_record(record2) == False


class TestRealWorldExamples:
    """Test with real-world examples from the codebase."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.filter = TrivialPatternFilter()
    
    def test_get_level_from_logging(self):
        """Test the actual get_level function from logging module."""
        code = '''
def get_level(self) -> int:
    """Get the current log level.

    Returns:
        The current minimum log level as an integer value.
    """
    return self.level
'''
        record = CodeRecord(code_content=code, function_name="get_level")
        assert self.filter.should_exclude_code_record(record) == True
    
    def test_to_dict_from_models(self):
        """Test the actual to_dict method from models."""
        code = '''
def to_dict(self) -> Dict[str, Any]:
    """Convert to dictionary for JSON serialization."""
    return {
        "id": self.id,
        "code_hash": self.code_hash,
        "function_name": self.function_name,
        "file_path": self.file_path,
    }
'''
        record = CodeRecord(code_content=code, function_name="to_dict")
        # This should NOT be excluded as it's more complex than trivial
        assert self.filter.should_exclude_code_record(record) == False
    
    def test_simple_repr_method(self):
        """Test simple __repr__ method."""
        code = '''
def __repr__(self) -> str:
    return f"{self.__class__.__name__}({self.message})"
'''
        record = CodeRecord(code_content=code, function_name="__repr__")
        assert self.filter.should_exclude_code_record(record) == True
    
    def test_pydantic_model_excluded(self):
        """Test that Pydantic models are excluded."""
        code = '''
class DeleteRequest(BaseModel):
    id: int = Field(..., description="ID of the record to delete")
'''
        record = CodeRecord(code_content=code, function_name="DeleteRequest")
        assert self.filter.should_exclude_code_record(record) == True
    
    def test_dataclass_excluded(self):
        """Test that dataclasses are excluded."""
        code = '''
@dataclass
class UserData:
    name: str
    age: int
'''
        record = CodeRecord(code_content=code, function_name="UserData")
        assert self.filter.should_exclude_code_record(record) == True
    
    def test_complex_class_not_excluded(self):
        """Test that complex classes are not excluded."""
        code = '''
class ComplexProcessor:
    def __init__(self, data):
        self.data = data
        self.cache = {}
    
    def process(self):
        if self.data in self.cache:
            return self.cache[self.data]
        
        result = self.expensive_computation()
        self.cache[self.data] = result
        return result
    
    def expensive_computation(self):
        # Complex logic here
        return sum(x * 2 for x in self.data if x > 0)
'''
        record = CodeRecord(code_content=code, function_name="ComplexProcessor")
        assert self.filter.should_exclude_code_record(record) == False