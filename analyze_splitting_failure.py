#!/usr/bin/env python3
"""
Analyze why the splitting is failing so badly with realistic data.
"""

import sys
import re
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, str(Path(__file__).parent / "src"))

from test_real_world_scenario import RealWorldDataGenerator


def analyze_function_patterns():
    """Analyze the patterns in realistic function names."""
    print("🔍 Analyzing Function Name Patterns")
    print("=" * 50)
    
    generator = RealWorldDataGenerator()
    functions = generator.generate_realistic_functions(1000)
    
    # Analyze naming patterns
    patterns = defaultdict(list)
    prefixes = Counter()
    suffixes = Counter()
    word_counts = Counter()
    
    for func in functions:
        name = func['name']
        category = func['category']
        patterns[category].append(name)
        
        # Analyze prefixes (first word)
        parts = name.split('_')
        if len(parts) > 0:
            prefixes[parts[0]] += 1
        
        # Analyze suffixes (last word)  
        if len(parts) > 1:
            suffixes[parts[-1]] += 1
        
        # Word count distribution
        word_counts[len(parts)] += 1
    
    print(f"📊 Generated {len(functions)} functions across {len(patterns)} categories")
    print(f"\nTop prefixes:")
    for prefix, count in prefixes.most_common(10):
        print(f"   {prefix}_*: {count} functions")
    
    print(f"\nWord count distribution:")
    for words, count in sorted(word_counts.items()):
        print(f"   {words} words: {count} functions ({count/len(functions)*100:.1f}%)")
    
    # Analyze why current patterns might fail
    print(f"\n🚨 Pattern Matching Analysis:")
    
    # Test current mock patterns against realistic data
    mock_patterns = [
        r'def\s+handle_\w*_(?:[0-46]\d{0,2})(?:_|\s*\()',
        r'def\s+process_\w*_(?:[0-86]\d{0,2})(?:_|\s*\()',
        r'def\s+\w+_[0-9]*[02468]\s*\(',
        r'async\s+def\s+'
    ]
    
    for pattern in mock_patterns:
        matches = 0
        for func in functions:
            if re.search(pattern, f"def {func['name']}():"):
                matches += 1
        
        match_rate = matches / len(functions) * 100
        print(f"   Pattern: {pattern[:30]}...")
        print(f"   Matches: {matches}/{len(functions)} ({match_rate:.1f}%)")
        
        if match_rate < 10:
            print(f"   ❌ PROBLEM: Very low match rate!")
        elif match_rate > 90:
            print(f"   ❌ PROBLEM: Too broad, no split!")
        else:
            print(f"   ✅ Reasonable split potential")
    
    # Suggest better patterns
    print(f"\n💡 Suggested Better Patterns:")
    
    # Category-based patterns
    for category, names in patterns.items():
        if len(names) > 50:  # Only analyze large categories
            sample_names = names[:5]
            common_starts = Counter()
            for name in names:
                parts = name.split('_')
                if len(parts) >= 2:
                    common_starts[f"{parts[0]}_{parts[1]}"] += 1
            
            if common_starts:
                top_pattern = common_starts.most_common(1)[0]
                pattern_base, count = top_pattern
                suggestion = f"def\\s+{pattern_base.replace('_', '_\\w*_')}.*"
                
                print(f"   {category}: {suggestion} (could match ~{count} functions)")


def analyze_splitting_algorithm_issues():
    """Analyze issues with the splitting algorithm itself."""
    print(f"\n🔧 Splitting Algorithm Analysis")
    print("=" * 40)
    
    # Test splitting behavior
    generator = RealWorldDataGenerator()
    functions = generator.generate_realistic_functions(500)
    
    print(f"📊 Testing with {len(functions)} realistic functions")
    
    # Simulate what happens in splitting
    categories = defaultdict(list)
    for func in functions:
        categories[func['category']].append(func)
    
    print(f"📋 Category distribution:")
    for cat, funcs in categories.items():
        print(f"   {cat}: {len(funcs)} functions")
    
    # Check if any single category dominates
    largest_category = max(categories.values(), key=len)
    largest_size = len(largest_category)
    largest_name = [k for k, v in categories.items() if len(v) == largest_size][0]
    
    print(f"\n🎯 Largest category: {largest_name} ({largest_size} functions)")
    
    if largest_size > len(functions) * 0.3:  # >30% in one category
        print(f"❌ PROBLEM: Category dominance! {largest_size/len(functions)*100:.1f}% in one category")
        print(f"   This means patterns won't split effectively")
    
    # Check naming diversity within categories
    print(f"\n📝 Naming diversity within categories:")
    for cat, funcs in list(categories.items())[:3]:  # Top 3 categories
        names = [f['name'] for f in funcs]
        unique_prefixes = len(set(name.split('_')[0] for name in names))
        print(f"   {cat}: {len(names)} functions, {unique_prefixes} unique prefixes")
        
        if unique_prefixes < 3:
            print(f"      ❌ LOW DIVERSITY: Hard to split with patterns")


def suggest_algorithm_improvements():
    """Suggest specific improvements to the algorithm."""
    print(f"\n🚀 Suggested Algorithm Improvements")
    print("=" * 40)
    
    improvements = [
        {
            'problem': 'Mock patterns don\'t match realistic function names',
            'solution': 'Dynamic pattern generation based on actual function name analysis',
            'implementation': 'Analyze function prefix/suffix distribution before generating patterns'
        },
        {
            'problem': 'Max depth limit prevents complete splitting',
            'solution': 'Adaptive depth limits based on group size reduction rate',
            'implementation': 'Continue splitting if groups are still >200 and reduction rate >20%'
        },
        {
            'problem': 'Single large categories dominate',
            'solution': 'Category-aware splitting strategy',  
            'implementation': 'Split by category first, then by naming patterns within categories'
        },
        {
            'problem': 'Patterns too generic or too specific',
            'solution': 'Multi-level pattern hierarchy',
            'implementation': 'Try coarse patterns first, then fine-grained patterns'
        }
    ]
    
    for i, improvement in enumerate(improvements, 1):
        print(f"{i}. {improvement['problem']}")
        print(f"   💡 Solution: {improvement['solution']}")
        print(f"   🔧 Implementation: {improvement['implementation']}")
        print()


if __name__ == "__main__":
    print("🚨 Splitting Failure Analysis")
    print("Investigating why large-scale splitting fails\n")
    
    analyze_function_patterns()
    analyze_splitting_algorithm_issues()  
    suggest_algorithm_improvements()
    
    print(f"\n🎯 Summary:")
    print("The current splitting algorithm has fundamental issues with:")
    print("1. Pattern matching for realistic function names")
    print("2. Handling category-diverse function sets")
    print("3. Depth limits that prevent complete splitting")
    print("4. Mock patterns that don't reflect real-world naming")
    print(f"\nImmediate action required before production use!")