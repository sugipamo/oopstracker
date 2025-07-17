# Trivial Pattern Filter

OOPStracker's trivial pattern filter helps reduce false positives by excluding common, acceptable patterns that appear as duplicates but are actually appropriate coding patterns.

## Overview

The trivial pattern filter automatically excludes:

- **Single-return functions** - Simple getter methods like `return self.value`
- **Simple special methods** - Basic `__str__`, `__repr__`, `__eq__` implementations
- **Trivial classes** - Empty classes with only `pass` statements
- **Simple properties** - Basic `@property` decorated getters
- **Short converter methods** - Basic `to_dict`, `to_json` methods (when enabled)

## Usage

### Command Line

By default, trivial patterns are excluded from duplicate detection:

```bash
# Default behavior - excludes trivial patterns
oopstracker check

# Include trivial patterns in results
oopstracker check --include-trivial
```

### Configuration

The filter behavior can be customized through the `TrivialFilterConfig` class:

```python
from oopstracker.trivial_filter import TrivialFilterConfig, TrivialPatternFilter

# Default configuration
config = TrivialFilterConfig()

# Custom configuration
config = TrivialFilterConfig(
    enable_single_return_filter=True,           # Level 1 (always recommended)
    enable_simple_special_method_filter=True,   # Level 1 (always recommended)
    enable_trivial_class_filter=True,           # Level 1 (always recommended)
    enable_simple_property_filter=True,         # Level 1 (always recommended)
    
    enable_short_function_filter=False,         # Level 2 (configurable)
    enable_simple_converter_filter=False,      # Level 2 (configurable)
    max_trivial_lines=3,                       # Threshold for short functions
    
    # Customize special methods to filter
    special_methods={'__str__', '__repr__', '__eq__', '__hash__'},
    
    # Customize converter methods to filter
    converter_methods={'to_dict', 'to_json', 'serialize'}
)

filter = TrivialPatternFilter(config)
```

## Filter Levels

### Level 1 (Always Applied)
These filters are always enabled and have high confidence:

- **Single Return Functions**: Functions with only `return self.property` or `return constant`
- **Simple Special Methods**: Basic implementations of `__str__`, `__repr__`, etc.
- **Trivial Classes**: Classes with only `pass` statements or minimal content
- **Simple Properties**: Basic `@property` decorated getters

### Level 2 (Configurable)
These filters can be optionally enabled:

- **Short Function Filter**: Very short functions (≤ 3 lines)
- **Simple Converter Filter**: Basic conversion methods like `to_dict`

## Examples

### Patterns That Are Excluded

```python
# Single return function
def get_level(self):
    return self.level

# Simple special method
def __str__(self):
    return self.name

# Trivial class
class EmptyClass:
    pass

# Simple property
@property
def name(self):
    return self._name

# Simple converter (when enabled)
def to_dict(self):
    return {"name": self.name}
```

### Patterns That Are NOT Excluded

```python
# Complex function with logic
def process_data(self, data):
    if not data:
        return None
    result = []
    for item in data:
        if item.is_valid():
            result.append(item.process())
    return result

# Complex special method
def __str__(self):
    parts = []
    if self.name:
        parts.append(f"Name: {self.name}")
    if self.value:
        parts.append(f"Value: {self.value}")
    return " - ".join(parts)

# Complex converter
def to_dict(self):
    result = {}
    for key, value in self.__dict__.items():
        if not key.startswith('_'):
            if hasattr(value, 'to_dict'):
                result[key] = value.to_dict()
            else:
                result[key] = value
    return result
```

## Implementation Details

### AST-Based Analysis
The filter uses AST (Abstract Syntax Tree) analysis to:
- Count actual code statements (excluding docstrings)
- Analyze return expressions
- Identify function patterns
- Detect decorators and special methods

### Performance Impact
- **Minimal**: AST analysis is performed only during filtering
- **Cached**: Results are cached for repeated checks
- **Efficient**: Most patterns are identified quickly

### Error Handling
- **Safe defaults**: If AST parsing fails, the code is NOT excluded
- **Graceful degradation**: Syntax errors don't prevent analysis
- **Logging**: Debug information available for troubleshooting

## Statistics and Reporting

Get exclusion statistics:

```python
from oopstracker.trivial_filter import TrivialPatternFilter
from oopstracker.models import CodeRecord

filter = TrivialPatternFilter()
records = [...]  # Your code records

# Get statistics
stats = filter.get_exclusion_stats(records)
print(f"Excluded {stats['excluded_count']} out of {stats['total_records']} records")
print(f"Exclusion rate: {stats['exclusion_percentage']:.1f}%")
```

## Best Practices

1. **Use Level 1 filters** - They have high confidence and low false positive rates
2. **Test Level 2 filters** - Enable them cautiously and verify results
3. **Monitor results** - Check exclusion statistics to ensure appropriate filtering
4. **Custom configuration** - Adjust special methods and converter methods for your codebase
5. **Use --include-trivial** - When you want to see all duplicates for comprehensive analysis

## Troubleshooting

### Too Many Exclusions
If too many legitimate duplicates are being excluded:
1. Check exclusion statistics with `get_exclusion_stats()`
2. Consider disabling Level 2 filters
3. Customize special methods and converter methods lists
4. Use `--include-trivial` to see all duplicates

### Too Few Exclusions
If trivial patterns are still showing up:
1. Verify the patterns match the supported types
2. Check if the code has complex logic mixed with simple patterns
3. Consider enabling Level 2 filters
4. Submit an issue with example code for pattern improvement

## Integration with OOPStracker

The trivial filter is automatically integrated into:
- **CLI commands** - Use `--include-trivial` to control behavior
- **AST detector** - Filtering applied during duplicate detection
- **API** - Available through `TrivialPatternFilter` class
- **Statistics** - Exclusion counts included in reports