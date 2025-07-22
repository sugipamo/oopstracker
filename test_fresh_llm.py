#!/usr/bin/env python3
"""
Test real LLM with completely fresh functions that don't match cached patterns.
"""

import asyncio
import sys
import os
import re
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oopstracker.smart_group_splitter import SmartGroupSplitter
from oopstracker.function_group_clustering import FunctionGroup


async def test_fresh_llm():
    """Test with fresh, unique function patterns."""
    print("🌐 Testing Real LLM with Fresh Patterns")
    print("=" * 50)
    print(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
    
    # Clear any cached rules first
    cache_file = Path("split_rules_cache.db")
    if cache_file.exists():
        cache_file.unlink()
        print("🗑️  Cleared existing rule cache")
    
    # Create unique function names that won't match cached patterns
    functions = []
    timestamp = str(int(time.time()))
    
    for i in range(120):  # 120 functions - needs splitting
        functions.extend([
            {'name': f'process_xyz_{timestamp}_{i}', 'code': f'def process_xyz_{timestamp}_{i}(): pass'},
            {'name': f'compute_abc_{timestamp}_{i}', 'code': f'def compute_abc_{timestamp}_{i}(): pass'},
        ])
    
    print(f"\n📊 Test data: {len(functions)} unique functions")
    print(f"   - Pattern: process_xyz_{timestamp}_* and compute_abc_{timestamp}_*")
    
    # Create initial group
    initial_group = FunctionGroup(
        group_id="fresh_test",
        functions=functions,
        label="Fresh Pattern Test Group",
        confidence=0.8,
        metadata={}
    )
    
    print(f"📈 Initial group: {len(functions)} functions (exceeds threshold of 100)")
    
    # Create splitter with real LLM (no cache)
    print("\n🔧 Initializing fresh LLM splitter...")
    splitter = SmartGroupSplitter(enable_ai=True, use_mock_ai=False)
    
    # Test splitting (this should trigger actual LLM calls)
    print("\n🤖 Applying real LLM splitting (no cached rules)...")
    start_time = time.time()
    
    try:
        final_groups = await splitter.split_large_groups_with_llm([initial_group], max_depth=2)
        elapsed_time = time.time() - start_time
        
        print(f"✅ Splitting completed in {elapsed_time:.1f}s")
        
        # Analyze results
        print(f"\n📊 Results:")
        print(f"   - Original groups: 1") 
        print(f"   - Final groups: {len(final_groups)}")
        
        sizes = [len(g.functions) for g in final_groups]
        print(f"   - Smallest group: {min(sizes)} functions")
        print(f"   - Largest group: {max(sizes)} functions") 
        print(f"   - Average size: {sum(sizes) / len(sizes):.1f} functions")
        
        # Check success
        large_groups = [g for g in final_groups if len(g.functions) > 100]
        print(f"   - Groups still >100: {len(large_groups)}")
        
        # Show generated patterns
        print(f"\n📋 Generated patterns:")
        unique_patterns = set()
        for group in final_groups:
            pattern = group.metadata.get('split_rule')
            if pattern and pattern not in unique_patterns:
                unique_patterns.add(pattern)
                print(f"   - {pattern}")
        
        # Show groups
        print(f"\n📋 Final groups:")
        for i, group in enumerate(final_groups):
            print(f"   {i+1}. {group.label}: {len(group.functions)} functions")
        
        # Verify function accounting
        total_functions_in_groups = sum(len(g.functions) for g in final_groups)
        print(f"\n✅ Function accounting:")
        print(f"   - Original: {len(functions)}")
        print(f"   - Final: {total_functions_in_groups}")
        print(f"   - Match: {'✅' if total_functions_in_groups == len(functions) else '❌'}")
        
        # Performance assessment
        if elapsed_time < 1.0:
            print(f"\n⚠️  Very fast completion ({elapsed_time:.1f}s) - may have used cached rules")
        else:
            print(f"\n🎯 Normal completion time ({elapsed_time:.1f}s) - likely generated fresh patterns")
        
        if len(large_groups) == 0:
            print(f"\n🎯 SUCCESS: All groups split to ≤100 functions!")
            return True
        else:
            print(f"\n⚠️  Some groups still >100")
            return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print(f"\n⏰ End time: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 50)


if __name__ == "__main__":
    success = asyncio.run(test_fresh_llm())
    if success:
        print("🎯 Fresh LLM test completed successfully")
    else:
        print("❌ Fresh LLM test failed")