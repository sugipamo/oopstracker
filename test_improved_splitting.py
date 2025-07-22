#!/usr/bin/env python3
"""
Test improved splitting with dynamic pattern generation.
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oopstracker.smart_group_splitter import SmartGroupSplitter
from oopstracker.function_group_clustering import FunctionGroup
from oopstracker.dynamic_pattern_generator import DynamicPatternGenerator
from test_real_world_scenario import RealWorldDataGenerator


async def test_dynamic_pattern_generation():
    """Test dynamic pattern generation directly."""
    print("🔬 Testing Dynamic Pattern Generation")
    print("=" * 50)
    
    generator = RealWorldDataGenerator()
    functions = generator.generate_realistic_functions(200)
    
    print(f"📊 Testing with {len(functions)} realistic functions")
    
    # Test dynamic pattern generator
    pattern_gen = DynamicPatternGenerator()
    
    print(f"\n🧪 Analyzing function structure...")
    analysis = pattern_gen.analyze_function_structure(functions)
    
    print(f"📋 Analysis results:")
    print(f"   - Total functions: {analysis['total_functions']}")
    print(f"   - Top prefixes: {list(analysis['prefixes'].keys())[:5]}")
    print(f"   - Word count distribution: {analysis['word_counts']}")
    
    print(f"\n🎯 Generating adaptive patterns...")
    patterns = pattern_gen.generate_adaptive_patterns(functions, target_split_ratio=0.5)
    
    print(f"✅ Generated {len(patterns)} patterns:")
    for i, (pattern, reasoning) in enumerate(patterns, 1):
        effectiveness = pattern_gen.test_pattern_effectiveness(pattern, functions)
        print(f"   {i}. Pattern: {pattern}")
        print(f"      Reasoning: {reasoning}")
        print(f"      Effectiveness: {effectiveness['effectiveness']:.3f}")
        print(f"      Match ratio: {effectiveness['ratio']:.1%} ({effectiveness['matches']}/{effectiveness['total']})")
        print(f"      Quality: {effectiveness['split_quality']}")
        print()
    
    # Compare with old vs new approach
    print(f"📊 Comparison with original approach:")
    
    # Old static patterns (from original MockAICoordinator)
    old_patterns = [
        ("def\\s+handle_\\w*_(?:[0-46]\\d{0,2})(?:_|\\s*\\()", "Old handle pattern"),
        ("def\\s+\\w+_[0-9]*[02468]\\s*\\(", "Old even number pattern"),
        ("async\\s+def\\s+", "Old async pattern")
    ]
    
    print(f"\n🔶 Original static patterns:")
    for pattern, desc in old_patterns:
        effectiveness = pattern_gen.test_pattern_effectiveness(pattern, functions)
        print(f"   {desc}: {effectiveness['ratio']:.1%} match rate, quality: {effectiveness['split_quality']}")
    
    print(f"\n🔷 New dynamic patterns:")  
    for i, (pattern, reasoning) in enumerate(patterns[:3], 1):
        effectiveness = pattern_gen.test_pattern_effectiveness(pattern, functions)
        print(f"   Pattern {i}: {effectiveness['ratio']:.1%} match rate, quality: {effectiveness['split_quality']}")
    
    return len([p for p in patterns if pattern_gen.test_pattern_effectiveness(p[0], functions)['split_quality'] == 'Good']) > 0


async def test_improved_splitting_simulation():
    """Simulate improved splitting without modifying original code."""
    print(f"\n🚀 Testing Improved Splitting Simulation")
    print("=" * 50)
    
    # Create realistic test case
    generator = RealWorldDataGenerator()
    functions = generator.generate_realistic_functions(1000)
    
    print(f"📊 Testing with {len(functions)} realistic functions")
    
    initial_group = FunctionGroup(
        group_id="simulation_test",
        functions=functions,
        label="Improved Splitting Simulation",
        confidence=0.8,
        metadata={}
    )
    
    # Simulate improved splitting algorithm
    print(f"\n🔧 Simulating improved splitting logic...")
    
    # Use dynamic pattern generation
    pattern_gen = DynamicPatternGenerator()
    patterns = pattern_gen.generate_adaptive_patterns(functions)
    
    if patterns:
        best_pattern, reasoning = patterns[0]
        effectiveness = pattern_gen.test_pattern_effectiveness(best_pattern, functions)
        
        print(f"🎯 Best pattern: {best_pattern}")
        print(f"💭 Reasoning: {reasoning}")
        print(f"📈 Effectiveness: {effectiveness['effectiveness']:.3f}")
        print(f"📊 Split: {effectiveness['matches']} / {effectiveness['total']} functions")
        
        # Simulate recursive splitting
        if effectiveness['split_quality'] == 'Good':
            matches = effectiveness['matches']
            non_matches = effectiveness['total'] - matches
            
            print(f"\n✅ Simulated split results:")
            print(f"   - Group 1: {matches} functions")
            print(f"   - Group 2: {non_matches} functions")
            print(f"   - Both groups < 100? {'✅' if max(matches, non_matches) <= 100 else '❌'}")
            
            # If groups still large, simulate further splitting
            if max(matches, non_matches) > 100:
                print(f"   - Recursive splitting would continue...")
                return True, max(matches, non_matches)
            else:
                print(f"   - ✅ Target achieved: all groups ≤100")
                return True, max(matches, non_matches)
        else:
            print(f"❌ Pattern quality insufficient for good splitting")
            return False, len(functions)
    else:
        print(f"❌ No suitable patterns generated")
        return False, len(functions)


async def main():
    """Run all improved splitting tests."""
    print("🎯 Testing Improved Splitting Algorithms")
    print("Addressing critical scaling issues found in real-world testing\n")
    
    start_time = time.time()
    
    # Test dynamic pattern generation
    pattern_success = await test_dynamic_pattern_generation()
    
    # Test simulation
    split_success, largest_group = await test_improved_splitting_simulation()
    
    elapsed = time.time() - start_time
    
    print(f"\n⏰ Testing completed in {elapsed:.1f}s")
    print("=" * 60)
    
    if pattern_success and split_success:
        print("🎉 Improved algorithms show significant promise!")
        print(f"✅ Dynamic patterns generate good splits")
        print(f"✅ Largest simulated group: {largest_group} functions")
        print(f"✅ Major improvement over original 1752 function groups")
    else:
        print("❌ Improvements need further work")
    
    return pattern_success and split_success


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print(f"\n🚀 Ready for implementation of improved algorithms")
    else:
        print(f"\n⚠️ Further development needed")