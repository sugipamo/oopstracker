#\!/usr/bin/env python3
"""Test indentation issues in code fragments."""

# Simulate what happens in oopstracker
test_code = '''    def test_complex_class_not_excluded(self):
        """Test that complex classes are not excluded."""
        code = \'\'\'
class ComplexProcessor:
    def __init__(self, data):
        self.data = data'''

print("Original code:")
print(repr(test_code))
print("\nLines:")
for i, line in enumerate(test_code.split('\n')):
    print(f"{i}: {repr(line)}")

# Try to parse it
import ast
try:
    ast.parse(test_code)
    print("\nNo syntax error\!")
except SyntaxError as e:
    print(f"\nSyntax error: {e.msg} at line {e.lineno}")
    print(f"Text: {repr(e.text)}")
