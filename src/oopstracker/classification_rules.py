"""Centralized classification rules for function categorization."""

from typing import List, Dict, Any
from .akinator_classifier import FunctionCategory


def get_default_rules() -> List[Dict[str, Any]]:
    """Get default classification rules."""
    return [
        {
            "rule_id": "getter_basic",
            "pattern": r"def\s+get_\w+\s*\(",
            "category": FunctionCategory.GETTER.value,
            "description": "Basic getter function pattern",
            "confidence": 0.8,
            "examples": ["def get_name(self):", "def get_value():"]
        },
        {
            "rule_id": "setter_basic", 
            "pattern": r"def\s+set_\w+\s*\(",
            "category": FunctionCategory.SETTER.value,
            "description": "Basic setter function pattern",
            "confidence": 0.8,
            "examples": ["def set_name(self, name):", "def set_value(value):"]
        },
        {
            "rule_id": "constructor_init",
            "pattern": r"def\s+__init__\s*\(",
            "category": FunctionCategory.CONSTRUCTOR.value,
            "description": "Constructor (__init__) method",
            "confidence": 0.95,
            "examples": ["def __init__(self):", "def __init__(self, name):"]
        },
        {
            "rule_id": "test_function",
            "pattern": r"def\s+test_\w+\s*\(",
            "category": FunctionCategory.TEST_FUNCTION.value,
            "description": "Test function pattern",
            "confidence": 0.9,
            "examples": ["def test_login():", "def test_validation():"]
        },
        {
            "rule_id": "async_function",
            "pattern": r"async\s+def\s+\w+\s*\(",
            "category": FunctionCategory.ASYNC_HANDLER.value,
            "description": "Async function pattern",
            "confidence": 0.9,
            "examples": ["async def fetch_data():", "async def process():"]
        },
        {
            "rule_id": "validation_function",
            "pattern": r"def\s+(validate|check|verify)_\w+\s*\(",
            "category": FunctionCategory.VALIDATION.value,
            "description": "Validation function pattern",
            "confidence": 0.85,
            "examples": ["def validate_email():", "def check_password():"]
        },
        {
            "rule_id": "conversion_function",
            "pattern": r"def\s+(to_|from_|convert_)\w+\s*\(",
            "category": FunctionCategory.CONVERSION.value,
            "description": "Conversion function pattern",
            "confidence": 0.85,
            "examples": ["def to_json():", "def from_dict():", "def convert_format():"]
        },
        # Additional patterns
        {
            "rule_id": "property_getter",
            "pattern": r"@property\s*\n\s*def\s+\w+",
            "category": FunctionCategory.GETTER.value,
            "description": "Property decorator getter",
            "confidence": 0.9,
            "examples": ["@property\ndef name(self):"]
        },
        {
            "rule_id": "error_handler",
            "pattern": r"def\s+(handle|catch|on)_\w*error\w*\s*\(",
            "category": FunctionCategory.ERROR_HANDLER.value,
            "description": "Error handling function",
            "confidence": 0.8,
            "examples": ["def handle_error():", "def on_connection_error():"]
        }
    ]


def get_pattern_keywords() -> Dict[str, List[str]]:
    """Get keywords for smart pattern generation."""
    return {
        "business_logic": ['process', 'handle', 'execute', 'perform', 'manage', 'calculate', 'analyze', 'compute'],
        "data_processing": ['transform', 'format', 'parse', 'serialize', 'filter', 'map', 'reduce', 'aggregate'],
        "validation": ['validate', 'check', 'verify', 'ensure', 'is_valid', 'can_'],
        "conversion": ['to_', 'from_', 'convert', 'transform', 'serialize', 'deserialize'],
        "utility": ['utils', 'helper', 'tools', 'common', 'shared'],
        "async_handler": ['async', 'await', 'fetch', 'request', 'callback']
    }