#!/usr/bin/env python3
"""Direct test of the refactored pattern generation logic."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Direct import to avoid package issues
from oopstracker.pattern_generator import PatternGenerator


def test_pattern_generator():
    """Test the PatternGenerator directly."""
    generator = PatternGenerator()
    
    print("Testing PatternGenerator...")
    print("-" * 60)
    
    # Test business logic patterns
    patterns = generator.generate_smart_patterns(
        "process_payment",
        "def process_payment(amount): return handle_transaction(amount)",
        "business_logic"
    )
    
    print(f"Business Logic Patterns for 'process_payment': {len(patterns)} found")
    for pattern in patterns:
        print(f"  - {pattern.get('description', 'N/A')}")
    
    # Test getter patterns
    patterns = generator.generate_smart_patterns(
        "get_user_name",
        "def get_user_name(self): return self.name",
        "getter"
    )
    
    print(f"\nGetter Patterns for 'get_user_name': {len(patterns)} found")
    for pattern in patterns:
        print(f"  - {pattern.get('description', 'N/A')}")
    
    # Test validation patterns
    patterns = generator.generate_smart_patterns(
        "validate_email",
        "def validate_email(email): return '@' in email and '.' in email",
        "validation"
    )
    
    print(f"\nValidation Patterns for 'validate_email': {len(patterns)} found")
    for pattern in patterns:
        print(f"  - {pattern.get('description', 'N/A')}")
    
    print("\n" + "-" * 60)
    print("PatternGenerator test completed successfully!")


if __name__ == "__main__":
    test_pattern_generator()