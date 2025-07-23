"""Function categories enumeration."""

from enum import Enum


class FunctionCategory(Enum):
    """Standard function categories."""
    GETTER = "getter"
    SETTER = "setter" 
    CONSTRUCTOR = "constructor"
    DESTRUCTOR = "destructor"
    UTILITY = "utility"
    BUSINESS_LOGIC = "business_logic"
    DATA_PROCESSING = "data_processing"
    VALIDATION = "validation"
    CONVERSION = "conversion"
    ASYNC_HANDLER = "async_handler"
    ERROR_HANDLER = "error_handler"
    TEST_FUNCTION = "test_function"
    DECORATOR = "decorator"
    CALCULATION = "calculation"  # Added for tax, total, etc calculations
    IO_OPERATION = "io_operation"  # File/network/database operations
    FACTORY = "factory"  # Factory pattern methods
    UNKNOWN = "unknown"