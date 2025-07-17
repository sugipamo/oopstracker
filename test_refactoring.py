#!/usr/bin/env python3
"""Test refactoring suggestions for the detected duplicates."""

from src.oopstracker.ast_simhash_detector import ASTSimHashDetector
from src.oopstracker.refactoring_analyzer import RefactoringAnalyzer

# Initialize detector
detector = ASTSimHashDetector()

# Find duplicates in test code
duplicates = detector.find_potential_duplicates(threshold=0.9)

# Group similar duplicates
duplicate_groups = []
current_group = []

for dup in duplicates:
    unit1, unit2, similarity = dup
    if similarity > 0.9:
        # Check if this belongs to current group
        if not current_group or any(u.function_name in [unit1.function_name, unit2.function_name] 
                                   for u, _, _ in current_group):
            current_group.append(dup)
        else:
            if current_group:
                duplicate_groups.append(current_group)
            current_group = [dup]

if current_group:
    duplicate_groups.append(current_group)

print(f"Found {len(duplicate_groups)} groups of related duplicates")

# Analyze with refactoring analyzer
refactoring_analyzer = RefactoringAnalyzer()

for i, group in enumerate(duplicate_groups[:3]):  # Analyze first 3 groups
    print(f"\n=== Group {i+1} ===")
    
    # Extract unique units from the group
    units = []
    seen_names = set()
    for unit1, unit2, similarity in group:
        if unit1.function_name not in seen_names:
            units.append(unit1)
            seen_names.add(unit1.function_name)
        if unit2.function_name not in seen_names:
            units.append(unit2)
            seen_names.add(unit2.function_name)
    
    print(f"Units in group: {[u.function_name for u in units]}")
    
    # Get refactoring recommendations
    recommendations = refactoring_analyzer.analyze_duplicates([units])
    
    for group_id, recs in recommendations.items():
        for rec in recs:
            print(f"  📋 {rec.refactoring_type.value}")
            print(f"     {rec.description}")
            print(f"     Confidence: {rec.confidence:.2f}")
            print(f"     ROI: {refactoring_analyzer.calculate_refactoring_roi(rec):.2f}")