"""
Refactored trivial filter that delegates to the new modular structure.
This acts as a facade to maintain backward compatibility.
"""

from typing import List, Optional
from .models import CodeRecord
from .filters import TrivialPatternFilter as NewTrivialFilter
from .filters import TrivialFilterConfig as NewConfig
from .filters import TrivialPatternAnalyzer as NewAnalyzer


# Re-export the config for backward compatibility
TrivialFilterConfig = NewConfig
TrivialPatternAnalyzer = NewAnalyzer


class TrivialPatternFilter:
    """
    Backward-compatible facade for the refactored trivial pattern filter.
    
    This class maintains the same interface as the original while delegating
    all operations to the new modular implementation in the filters package.
    """
    
    def __init__(self, config: Optional[TrivialFilterConfig] = None, include_tests: bool = False):
        """Initialize the filter with optional configuration."""
        self._filter = NewTrivialFilter(config, include_tests)
        
        # Expose the same attributes for compatibility
        self.config = self._filter.config
        self.include_tests = self._filter.include_tests
    
    def should_exclude_code_record(self, record: CodeRecord) -> bool:
        """Check if a CodeRecord should be excluded as trivial."""
        return self._filter.should_exclude_code_record(record)
    
    def filter_records(self, records: List[CodeRecord]) -> List[CodeRecord]:
        """Filter a list of CodeRecords, removing trivial patterns."""
        return self._filter.filter_records(records)
    
    def get_exclusion_stats(self, records: List[CodeRecord]) -> dict:
        """Get statistics about what was excluded and why."""
        return self._filter.get_exclusion_stats(records)
    
    # Backward compatibility method aliases
    def _is_test_function_name(self, function_name: str) -> bool:
        """Check if a function name indicates it's a test function."""
        return self._filter._is_test_function_name(function_name)