"""
Simple test to verify the refactored AST analyzer works.
"""

import sys
import os

# Test the new modular structure
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from oopstracker.ast_analysis import ASTAnalyzer, CodeUnit, SimilarityCalculator


def test_basic_parsing():
    """Test basic parsing functionality."""
    test_code = '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
'''
    
    analyzer = ASTAnalyzer()
    units = analyzer.parse_code(test_code)
    
    print(f"Found {len(units)} code units:")
    for unit in units:
        print(f"  - {unit.type} '{unit.name}'")
        print(f"    Lines: {unit.start_line}-{unit.end_line}")
        print(f"    Complexity: {unit.complexity_score}")
        print(f"    Dependencies: {unit.dependencies}")
        if unit.ast_structure:
            tokens = unit.ast_structure.split('|')
            print(f"    Structure tokens: {len(tokens)}")
            print(f"    First 5 tokens: {tokens[:5]}")
        print()
    
    assert len(units) == 2, f"Expected 2 units, got {len(units)}"
    assert units[0].name == "add"
    assert units[1].name == "Calculator"
    
    print("✅ Basic parsing test PASSED\n")


def test_similarity():
    """Test similarity calculation."""
    code1 = '''
def process(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
'''
    
    code2 = '''
def handle(items):
    output = []
    for x in items:
        if x > 0:
            output.append(x * 2)
    return output
'''
    
    analyzer = ASTAnalyzer()
    units1 = analyzer.parse_code(code1)
    units2 = analyzer.parse_code(code2)
    
    calc = SimilarityCalculator()
    similarity = calc.calculate_structural_similarity(units1[0], units2[0])
    
    print(f"Similarity between functions: {similarity:.3f}")
    assert similarity > 0.8, f"Expected high similarity, got {similarity}"
    
    print("✅ Similarity test PASSED\n")


def test_complex_structure():
    """Test with complex code structure."""
    code = '''
class DataProcessor:
    def process(self, data):
        try:
            with open("file.txt") as f:
                content = f.read()
            
            for line in content.split("\\n"):
                if line.strip():
                    self._handle_line(line)
        except IOError as e:
            print(f"Error: {e}")
        finally:
            self._cleanup()
    
    def _handle_line(self, line):
        pass
    
    def _cleanup(self):
        pass
'''
    
    analyzer = ASTAnalyzer()
    units = analyzer.parse_code(code)
    
    print(f"Found {len(units)} units in complex code")
    
    # Find the process method
    process_unit = next(u for u in units if u.name == "process")
    print(f"\nProcess method analysis:")
    print(f"  Complexity: {process_unit.complexity_score}")
    print(f"  Dependencies: {process_unit.dependencies}")
    
    # Check for expected structure tokens
    tokens = process_unit.ast_structure.split('|') if process_unit.ast_structure else []
    token_types = [t.split(':')[0] for t in tokens]
    
    assert 'TRY' in token_types, "Missing TRY token"
    assert 'WITH' in token_types, "Missing WITH token"
    assert 'FOR' in token_types, "Missing FOR token"
    assert 'IF' in token_types, "Missing IF token"
    
    print("✅ Complex structure test PASSED\n")


if __name__ == "__main__":
    print("Testing refactored AST analyzer...\n")
    
    try:
        test_basic_parsing()
        test_similarity()
        test_complex_structure()
        
        print("🎉 All tests PASSED!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()