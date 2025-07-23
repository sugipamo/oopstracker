#!/usr/bin/env python3
"""Test script to verify the refactored AkinatorClassifier works correctly."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from oopstracker.akinator_classifier import AkinatorClassifier


def test_basic_classification():
    """Test basic function classification after refactoring."""
    classifier = AkinatorClassifier()
    
    # Test cases
    test_cases = [
        ("def get_name(self): return self._name", "get_name", "getter"),
        ("def set_value(self, val): self.value = val", "set_value", "setter"),
        ("def __init__(self, name): self.name = name", "__init__", "constructor"),
        ("def validate_email(email): return '@' in email", "validate_email", "validation"),
    ]
    
    print("Testing AkinatorClassifier after refactoring...")
    print("-" * 60)
    
    for func_code, func_name, expected_category in test_cases:
        result = classifier.classify_function(func_code, func_name)
        success = result.category == expected_category
        
        print(f"Function: {func_name}")
        print(f"Expected: {expected_category}")
        print(f"Actual: {result.category}")
        print(f"Confidence: {result.confidence}")
        print(f"Success: {'✓' if success else '✗'}")
        print("-" * 60)


def test_pattern_generation():
    """Test pattern generation through the new PatternGenerator."""
    classifier = AkinatorClassifier()
    
    # Test pattern generation
    patterns = classifier._generate_smart_patterns(
        "process_payment", 
        "def process_payment(amount): return handle_transaction(amount)",
        "business_logic"
    )
    
    print("\nTesting pattern generation...")
    print("-" * 60)
    print(f"Generated {len(patterns)} patterns for 'process_payment':")
    
    for pattern in patterns:
        print(f"- Pattern: {pattern.get('pattern', 'N/A')}")
        print(f"  Type: {pattern.get('type', 'N/A')}")
        print(f"  Description: {pattern.get('description', 'N/A')}")
        print(f"  Confidence: {pattern.get('confidence', 'N/A')}")
        print()


if __name__ == "__main__":
    test_basic_classification()
    test_pattern_generation()
    print("\nRefactoring test completed!")