#\!/usr/bin/env python3
"""Test code extraction to find indentation issues."""

import sys
import os

# Add oopstracker to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from oopstracker.models import CodeRecord
from oopstracker.ast_simhash_detector import ASTSimHashDetector

# Create detector
detector = ASTSimHashDetector()

# Test code with potential indentation issue
test_code = '''def test_complex_class_not_excluded(self):
    """Test that complex classes are not excluded."""
    code = \'\'\'
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
\'\'\'
    record = CodeRecord(code_content=code, function_name="ComplexProcessor")
    assert self.filter.should_exclude_code_record(record) == False'''

# Register the test code
detector.register_code(test_code, "test_complex_class_not_excluded", "test.py")

# Find the registered record
for record in detector.code_records:
    if record.function_name == "test_complex_class_not_excluded":
        print("Found record:")
        print(f"Function: {record.function_name}")
        print(f"Code length: {len(record.code_content)}")
        print("First 100 chars of code:")
        print(repr(record.code_content[:100]))
        print("\nChecking for indentation issues...")
        
        # Check each line
        lines = record.code_content.split('\n')
        for i, line in enumerate(lines):
            if line.strip() and not line[0].isspace() and i > 0:
                # Line starts without indentation after first line
                if lines[i-1].strip().endswith(':'):
                    print(f"  Issue at line {i+1}: Expected indentation after ':'")
                    print(f"    Previous: {repr(lines[i-1])}")
                    print(f"    Current:  {repr(line)}")
        break
