#!/usr/bin/env python3
"""
Simple test for 5000 files with mock LLM.
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oopstracker.ast_analyzer import CodeUnit
from oopstracker.smart_group_splitter import SmartGroupSplitter
from oopstracker.function_group_clustering import FunctionGroup


def create_test_functions(num_files=5000, funcs_per_file=3):
    """Create test functions for simulation."""
    functions = []
    modules = ['auth', 'api', 'database', 'business', 'integration', 'utils', 'frontend', 'testing']
    
    for i in range(num_files):
        module = modules[i % len(modules)]
        for j in range(funcs_per_file):
            func_name = f"{module}_function_{i}_{j}"
            functions.append({
                'name': func_name,
                'code': f'def {func_name}(): pass',
                'file_path': f'{module}/file_{i}.py',
                'module': module
            })
    
    return functions


async def test_5000_files_mock():
    """Test with 5000 files using mock LLM."""
    print("🚀 Testing 5000 Files with Mock LLM (Simple)")
    print("=" * 60)
    print(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
    
    # Configuration
    NUM_FILES = 5000
    FUNCTIONS_PER_FILE = 3
    
    print(f"\n📊 Configuration:")
    print(f"   Files: {NUM_FILES:,}")
    print(f"   Functions per file: {FUNCTIONS_PER_FILE}")
    print(f"   Total functions: {NUM_FILES * FUNCTIONS_PER_FILE:,}")
    print(f"   Using: Mock LLM")
    
    # Generate test data
    print("\n📁 Generating test data...")
    start_time = time.time()
    functions = create_test_functions(NUM_FILES, FUNCTIONS_PER_FILE)
    data_gen_time = time.time() - start_time
    print(f"   ✅ Generated {len(functions):,} functions in {data_gen_time:.1f}s")
    
    # Create initial groups by module
    print("\n🔧 Creating initial groups by module...")
    start_time = time.time()
    
    # Group functions by module
    module_groups = {}
    for func in functions:
        module = func['module']
        if module not in module_groups:
            module_groups[module] = []
        module_groups[module].append(func)
    
    # Create FunctionGroup objects
    initial_groups = []
    for module, funcs in module_groups.items():
        group = FunctionGroup(
            group_id=f"group_{module}",
            functions=funcs,
            label=f"{module.title()} Module",
            confidence=0.8,
            metadata={'module': module}
        )
        initial_groups.append(group)
    
    clustering_time = time.time() - start_time
    print(f"   ✅ Created {len(initial_groups)} initial groups in {clustering_time:.1f}s")
    
    # Show initial group sizes
    print("\n   Initial group sizes:")
    for group in initial_groups:
        print(f"   - {group.label}: {len(group.functions):,} functions")
    
    # Apply smart splitting
    print("\n🤖 Applying LLM-based smart splitting...")
    print("   Threshold: >100 functions per group")
    start_time = time.time()
    
    splitter = SmartGroupSplitter(enable_ai=True, use_mock_ai=True)
    
    # Count groups needing split
    groups_needing_split = len([g for g in initial_groups if len(g.functions) > 100])
    print(f"   Groups needing LLM split: {groups_needing_split}")
    
    final_groups = await splitter.split_large_groups_with_llm(initial_groups)
    
    splitting_time = time.time() - start_time
    print(f"   ✅ Split into {len(final_groups)} final groups in {splitting_time:.1f}s")
    
    # Analysis
    print("\n📈 Results Analysis:")
    
    # Group size distribution
    sizes = [len(g.functions) for g in final_groups]
    print(f"\n   Group sizes:")
    print(f"   - Smallest: {min(sizes)} functions")
    print(f"   - Largest: {max(sizes)} functions")
    print(f"   - Average: {sum(sizes) / len(sizes):.1f} functions")
    
    # Groups by size category
    tiny = len([s for s in sizes if s < 10])
    small = len([s for s in sizes if 10 <= s < 50])
    medium = len([s for s in sizes if 50 <= s <= 100])
    large = len([s for s in sizes if s > 100])
    
    print(f"\n   Size distribution:")
    print(f"   - Small (10-49): {small} groups")
    print(f"   - Medium (50-100): {medium} groups")
    print(f"   - Large (>100): {large} groups")
    
    # Performance metrics
    total_time = data_gen_time + clustering_time + splitting_time
    print(f"\n⏱️  Performance Summary:")
    print(f"   - Data generation: {data_gen_time:.1f}s")
    print(f"   - Initial grouping: {clustering_time:.1f}s")
    print(f"   - LLM splitting: {splitting_time:.1f}s")
    print(f"   - Total time: {total_time:.1f}s")
    
    # Check if any groups are still too large
    if large > 0:
        print(f"\n⚠️  Warning: {large} groups still have >100 functions")
        print("   These hit the maximum split depth")
        largest_groups = sorted(final_groups, key=lambda g: len(g.functions), reverse=True)[:3]
        for g in largest_groups:
            if len(g.functions) > 100:
                split_count = g.metadata.get('split_count', 0)
                print(f"   - {g.label}: {len(g.functions)} functions (split {split_count} times)")
    else:
        print("\n✅ All groups successfully split to ≤100 functions!")
    
    print(f"\n⏰ End time: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    # Estimate real LLM time
    if groups_needing_split > 0:
        # Assume 2 seconds per real LLM call + 3 retries worst case
        theoretical_llm_time = groups_needing_split * 2.0 * 3  # With retries
        print(f"\n💭 Estimated time with real LLM:")
        print(f"   - LLM calls needed: {groups_needing_split}")
        print(f"   - Time per call (with retries): ~6s")
        print(f"   - Total LLM time: {theoretical_llm_time:.1f}s ({theoretical_llm_time/60:.1f} minutes)")
        print(f"   - Total time: {data_gen_time + clustering_time + theoretical_llm_time:.1f}s")


if __name__ == "__main__":
    asyncio.run(test_5000_files_mock())