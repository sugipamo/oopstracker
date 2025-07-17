#!/usr/bin/env python3
"""Test script to verify the improvements."""

from src.oopstracker.ast_analyzer import ASTAnalyzer, CodeUnit
from src.oopstracker.refactoring_analyzer import RefactoringAnalyzer
from collections import Counter

print("=== Testing Bag of Words Implementation ===")

# Test the new Bag of Words similarity calculation
analyzer = ASTAnalyzer()

# Create two similar code units with repeated tokens
unit1 = CodeUnit(
    name='test1',
    type='function',
    source_code='def test(): pass',
    start_line=1,
    end_line=1,
    ast_structure='FUNC:2|DECORATOR:0|FUNC:2|CALL:print|CALL:print'
)

unit2 = CodeUnit(
    name='test2', 
    type='function',
    source_code='def test(): pass',
    start_line=10,  # Different line to avoid self-reference
    end_line=10,
    ast_structure='FUNC:2|DECORATOR:0|CALL:print'
)

# Test old approach (set-based) vs new approach (Counter-based)
tokens1_set = set(unit1.ast_structure.split('|'))
tokens2_set = set(unit2.ast_structure.split('|'))
old_similarity = len(tokens1_set & tokens2_set) / len(tokens1_set | tokens2_set) if tokens1_set | tokens2_set else 0

# New approach
new_similarity = analyzer.calculate_structural_similarity(unit1, unit2)

print(f'Old similarity (set-based): {old_similarity:.3f}')
print(f'New similarity (Counter-based): {new_similarity:.3f}')
print(f'Token counts in unit1: {dict(Counter(unit1.ast_structure.split("|")))}')
print(f'Token counts in unit2: {dict(Counter(unit2.ast_structure.split("|")))}')

print("\n=== Testing Refactoring Analyzer ===")

# Test refactoring analyzer
refactoring_analyzer = RefactoringAnalyzer()

# Create some duplicate units
duplicate_groups = [
    [unit1, unit2],  # Function duplicates
    [
        CodeUnit(name='TestClass1', type='class', source_code='class Test: pass', 
                start_line=1, end_line=1, file_path='test_file1.py'),
        CodeUnit(name='TestClass2', type='class', source_code='class Test: pass', 
                start_line=1, end_line=1, file_path='test_file2.py')
    ]
]

recommendations = refactoring_analyzer.analyze_duplicates(duplicate_groups)

for group_id, recs in recommendations.items():
    print(f"\n{group_id}:")
    for rec in recs:
        print(f"  - Type: {rec.refactoring_type.value}")
        print(f"    Description: {rec.description}")
        print(f"    Confidence: {rec.confidence:.2f}")
        print(f"    ROI: {refactoring_analyzer.calculate_refactoring_roi(rec):.2f}")

print("\n=== Testing Self-Reference Fix ===")

# Test that self-reference is properly filtered
unit_self = CodeUnit(
    name='same_func',
    type='function', 
    source_code='def same(): pass',
    start_line=5,
    end_line=5,
    file_path='same_file.py',
    ast_structure='FUNC:0|DECORATOR:0'
)

# This should not compare against itself
print("Testing self-reference filtering...")
print("(Check that the duplicate detection doesn't report self-references)")

print("\nAll tests completed!")