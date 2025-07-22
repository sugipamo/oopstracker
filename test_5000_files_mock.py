#!/usr/bin/env python3
"""
Test 5000 files with mock LLM to verify the algorithm works.
"""

import asyncio
import sys
import time
import random
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oopstracker.smart_group_splitter import SmartGroupSplitter
from oopstracker.function_group_clustering import FunctionGroup, FunctionGroupClusteringSystem
from oopstracker.models import CodeRecord


async def test_5000_files_mock():
    """Test with 5000 files using mock LLM."""
    print("🚀 Testing 5000 Files with Mock LLM")
    print("=" * 60)
    print(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
    
    # Configuration
    NUM_FILES = 5000
    FUNCTIONS_PER_FILE = 3  # Average 3 functions per file = 15,000 total
    
    print(f"\n📊 Configuration:")
    print(f"   Files: {NUM_FILES:,}")
    print(f"   Functions per file: {FUNCTIONS_PER_FILE}")
    print(f"   Total functions: {NUM_FILES * FUNCTIONS_PER_FILE:,}")
    print(f"   Using: Mock LLM (fast responses)")
    
    # Generate test data
    print("\n📁 Generating test data...")
    start_time = time.time()
    
    modules = ['auth', 'api', 'database', 'business', 'integration', 'utils', 'frontend', 'testing']
    code_records = []
    
    for i in range(NUM_FILES):
        module = modules[i % len(modules)]
        file_path = f"{module}/file_{i}.py"
        
        # Generate functions for this file
        for j in range(FUNCTIONS_PER_FILE):
            func_name = f"{module}_function_{i}_{j}"
            code = f"def {func_name}(): pass"
            
            record = CodeRecord(
                function_name=func_name,
                file_path=file_path,
                code_content=code,
                code_hash=f"hash_{i}_{j}",
                metadata={
                    'start_line': j * 2 + 1,
                    'end_line': j * 2 + 2,
                    'func_id': f"id_{i}_{j}"
                }
            )
            code_records.append(record)
    
    data_gen_time = time.time() - start_time
    print(f"   ✅ Generated {len(code_records):,} functions in {data_gen_time:.1f}s")
    
    # Initial clustering
    print("\n🔧 Performing initial clustering...")
    start_time = time.time()
    
    clusterer = FunctionGroupClusteringSystem(use_mock_ai=True)
    initial_groups = await clusterer.cluster_functions(code_records)
    
    clustering_time = time.time() - start_time
    print(f"   ✅ Created {len(initial_groups)} initial groups in {clustering_time:.1f}s")
    
    # Apply smart splitting
    print("\n🤖 Applying LLM-based smart splitting...")
    print("   Threshold: >100 functions per group")
    start_time = time.time()
    
    splitter = SmartGroupSplitter(use_mock_ai=True)
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
    print(f"   - Median: {sorted(sizes)[len(sizes)//2]} functions")
    
    # Groups by size category
    tiny = len([s for s in sizes if s < 10])
    small = len([s for s in sizes if 10 <= s < 50])
    medium = len([s for s in sizes if 50 <= s <= 100])
    large = len([s for s in sizes if s > 100])
    
    print(f"\n   Size distribution:")
    print(f"   - Tiny (<10): {tiny} groups")
    print(f"   - Small (10-49): {small} groups")
    print(f"   - Medium (50-100): {medium} groups")
    print(f"   - Large (>100): {large} groups")
    
    # Performance metrics
    total_time = data_gen_time + clustering_time + splitting_time
    print(f"\n⏱️  Performance Summary:")
    print(f"   - Data generation: {data_gen_time:.1f}s")
    print(f"   - Initial clustering: {clustering_time:.1f}s")
    print(f"   - LLM splitting: {splitting_time:.1f}s")
    print(f"   - Total time: {total_time:.1f}s")
    print(f"   - Functions/second: {len(code_records) / total_time:.0f}")
    
    # LLM usage estimate
    llm_calls = len([g for g in initial_groups if len(g.functions) > 100])
    print(f"\n🤖 LLM Usage:")
    print(f"   - Groups requiring LLM split: {llm_calls}")
    print(f"   - Average time per LLM call: {splitting_time / max(llm_calls, 1):.2f}s")
    
    # Check if any groups are still too large
    if large > 0:
        print(f"\n⚠️  Warning: {large} groups still have >100 functions")
        print("   These hit the maximum split depth (3)")
        largest_groups = sorted(final_groups, key=lambda g: len(g.functions), reverse=True)[:5]
        for g in largest_groups:
            if len(g.functions) > 100:
                print(f"   - {g.label}: {len(g.functions)} functions")
    else:
        print("\n✅ All groups successfully split to ≤100 functions!")
    
    print(f"\n⏰ End time: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    # Save split rules for inspection
    if hasattr(splitter, 'rule_repository'):
        rules = splitter.rule_repository.get_all_rules()
        print(f"\n📋 Generated {len(rules)} splitting rules (saved in SQLite)")
        if rules:
            print("   Sample rules:")
            for rule in rules[:3]:
                print(f"   - Pattern: {rule.pattern}")
                print(f"     Reason: {rule.reasoning[:50]}...")


if __name__ == "__main__":
    asyncio.run(test_5000_files_mock())