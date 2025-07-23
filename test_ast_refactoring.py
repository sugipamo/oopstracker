"""
Test script to verify the refactored AST analyzer works correctly.
"""

import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from oopstracker.ast_analyzer import ASTAnalyzer as OldAnalyzer
from oopstracker.ast_analyzer_refactored import ASTAnalyzer as NewAnalyzer


def test_basic_functionality():
    """Test basic parsing and analysis functionality."""
    test_code = '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def multiply(x, y):
    """Multiply two numbers."""
    result = x * y
    return result

class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, a, b):
        self.result = a + b
        return self.result
'''
    
    # Test with old analyzer
    print("Testing OLD analyzer...")
    old_analyzer = OldAnalyzer()
    old_units = old_analyzer.parse_code(test_code)
    
    print(f"Found {len(old_units)} code units with old analyzer")
    for unit in old_units:
        print(f"  - {unit.type} {unit.name}: {len(unit.ast_structure.split('|')) if unit.ast_structure else 0} tokens")
    
    # Test with new analyzer
    print("\nTesting NEW analyzer...")
    new_analyzer = NewAnalyzer()
    new_units = new_analyzer.parse_code(test_code)
    
    print(f"Found {len(new_units)} code units with new analyzer")
    for unit in new_units:
        print(f"  - {unit.type} {unit.name}: {len(unit.ast_structure.split('|')) if unit.ast_structure else 0} tokens")
    
    # Compare results
    assert len(old_units) == len(new_units), f"Unit count mismatch: {len(old_units)} vs {len(new_units)}"
    
    for old_unit, new_unit in zip(old_units, new_units):
        assert old_unit.name == new_unit.name, f"Name mismatch: {old_unit.name} vs {new_unit.name}"
        assert old_unit.type == new_unit.type, f"Type mismatch: {old_unit.type} vs {new_unit.type}"
        assert old_unit.start_line == new_unit.start_line, f"Start line mismatch: {old_unit.start_line} vs {new_unit.start_line}"
        assert old_unit.end_line == new_unit.end_line, f"End line mismatch: {old_unit.end_line} vs {new_unit.end_line}"
    
    print("\n✅ Basic functionality test PASSED")


def test_similarity_calculation():
    """Test similarity calculation between code units."""
    test_code1 = '''
def process_data(data):
    if not data:
        return None
    
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
'''
    
    test_code2 = '''
def handle_items(items):
    if not items:
        return None
    
    output = []
    for element in items:
        if element > 0:
            output.append(element * 2)
    return output
'''
    
    # Test with both analyzers
    old_analyzer = OldAnalyzer()
    new_analyzer = NewAnalyzer()
    
    old_units1 = old_analyzer.parse_code(test_code1)
    old_units2 = old_analyzer.parse_code(test_code2)
    
    new_units1 = new_analyzer.parse_code(test_code1)
    new_units2 = new_analyzer.parse_code(test_code2)
    
    # Calculate similarity
    old_similarity = old_analyzer.calculate_structural_similarity(old_units1[0], old_units2[0])
    new_similarity = new_analyzer.calculate_structural_similarity(new_units1[0], new_units2[0])
    
    print(f"\nSimilarity calculation:")
    print(f"  Old analyzer: {old_similarity:.3f}")
    print(f"  New analyzer: {new_similarity:.3f}")
    
    # They should be very similar (allowing for small differences due to refactoring)
    assert abs(old_similarity - new_similarity) < 0.1, f"Similarity difference too large: {abs(old_similarity - new_similarity)}"
    
    print("✅ Similarity calculation test PASSED")


def test_complex_code():
    """Test with more complex code structures."""
    test_code = '''
class DataProcessor:
    def __init__(self, config):
        self.config = config
        self.data = []
    
    def process(self, items):
        try:
            for item in items:
                if self._validate(item):
                    processed = self._transform(item)
                    self.data.append(processed)
        except Exception as e:
            print(f"Error: {e}")
            raise
        finally:
            self._cleanup()
    
    def _validate(self, item):
        return item is not None and item > 0
    
    def _transform(self, item):
        return item * 2 if item % 2 == 0 else item + 1
    
    def _cleanup(self):
        pass
'''
    
    old_analyzer = OldAnalyzer()
    new_analyzer = NewAnalyzer()
    
    old_units = old_analyzer.parse_code(test_code)
    new_units = new_analyzer.parse_code(test_code)
    
    print(f"\nComplex code analysis:")
    print(f"  Old analyzer found {len(old_units)} units")
    print(f"  New analyzer found {len(new_units)} units")
    
    assert len(old_units) == len(new_units), "Unit count mismatch for complex code"
    
    # Check complexity scores
    for old_unit, new_unit in zip(old_units, new_units):
        print(f"  {old_unit.name}: old_complexity={old_unit.complexity_score}, new_complexity={new_unit.complexity_score}")
        # Complexity should be preserved
        assert old_unit.complexity_score == new_unit.complexity_score, f"Complexity mismatch for {old_unit.name}"
    
    print("✅ Complex code test PASSED")


def test_simhash_generation():
    """Test SimHash generation."""
    test_code = '''
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total
'''
    
    old_analyzer = OldAnalyzer()
    new_analyzer = NewAnalyzer()
    
    old_units = old_analyzer.parse_code(test_code)
    new_units = new_analyzer.parse_code(test_code)
    
    old_hash = old_analyzer.generate_ast_simhash(old_units[0])
    new_hash = new_analyzer.generate_ast_simhash(new_units[0])
    
    print(f"\nSimHash generation:")
    print(f"  Old analyzer: {old_hash}")
    print(f"  New analyzer: {new_hash}")
    
    # SimHash should be identical
    assert old_hash == new_hash, f"SimHash mismatch: {old_hash} vs {new_hash}"
    
    print("✅ SimHash generation test PASSED")


if __name__ == "__main__":
    print("Running AST analyzer refactoring tests...\n")
    
    try:
        test_basic_functionality()
        test_similarity_calculation()
        test_complex_code()
        test_simhash_generation()
        
        print("\n🎉 All tests PASSED! The refactoring is working correctly.")
    except AssertionError as e:
        print(f"\n❌ Test FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)