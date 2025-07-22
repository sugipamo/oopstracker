#!/usr/bin/env python3
"""
Force actual LLM calls by bypassing cache and using verbose logging.
"""

import asyncio
import sys
import os
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oopstracker.smart_group_splitter import SmartGroupSplitter
from oopstracker.function_group_clustering import FunctionGroup
from oopstracker.ai_analysis_coordinator import get_ai_coordinator


async def test_force_llm_call():
    """Force actual LLM call with detailed logging."""
    print("🌐 Testing Forced Real LLM Calls")
    print("=" * 50)
    print(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
    
    # Remove any cache files
    for cache_file in Path(".").glob("*cache*.db"):
        cache_file.unlink()
        print(f"🗑️  Removed cache: {cache_file}")
    
    # Create unique test functions
    unique_id = str(int(time.time() * 1000))[-6:]  # Last 6 digits of timestamp
    functions = []
    
    for i in range(110):  # Just over threshold
        functions.append({
            'name': f'unique_func_{unique_id}_{i:03d}',
            'code': f'def unique_func_{unique_id}_{i:03d}(param): return param * {i}'
        })
    
    print(f"\n📊 Test data: {len(functions)} unique functions with ID {unique_id}")
    
    # Create initial group
    initial_group = FunctionGroup(
        group_id=f"test_{unique_id}",
        functions=functions,
        label=f"Unique Test Group {unique_id}",
        confidence=0.8,
        metadata={}
    )
    
    # Direct LLM test first
    print(f"\n🔧 Testing direct LLM call...")
    coordinator = get_ai_coordinator(use_mock=False)
    
    sample_functions = functions[:3]
    function_list = "\n".join([
        f"Function: {func['name']}\nCode: {func['code']}\n"
        for func in sample_functions
    ])
    
    prompt = f"""以下の関数を2つのグループに分割する正規表現を作成してください：

{function_list}

回答形式：
PATTERN: <正規表現>
REASONING: <理由>"""
    
    print(f"📤 Sending prompt to LLM...")
    start_llm = time.time()
    
    try:
        response = await coordinator.analyze_intent(prompt)
        elapsed_llm = time.time() - start_llm
        
        print(f"✅ LLM response received in {elapsed_llm:.1f}s")
        print(f"   Success: {response.success}")
        
        if response.success:
            result_text = response.result.get('purpose', '') if isinstance(response.result, dict) else str(response.result)
            print(f"   Response preview: {result_text[:100]}...")
            
            # Check for pattern
            import re
            pattern_match = re.search(r'PATTERN:\s*([^\n]+)', result_text, re.IGNORECASE)
            if pattern_match:
                pattern = pattern_match.group(1).strip()
                print(f"   ✅ Extracted pattern: {pattern}")
            else:
                print(f"   ⚠️  No PATTERN found in response")
        
    except Exception as e:
        print(f"❌ Direct LLM call failed: {e}")
        return False
    
    # Now test full splitting
    print(f"\n🤖 Testing full splitting process...")
    splitter = SmartGroupSplitter(enable_ai=True, use_mock_ai=False)
    
    start_split = time.time()
    try:
        final_groups = await splitter.split_large_groups_with_llm([initial_group], max_depth=2)
        elapsed_split = time.time() - start_split
        
        print(f"✅ Splitting completed in {elapsed_split:.1f}s")
        
        # Results
        print(f"\n📊 Results:")
        print(f"   - Original groups: 1")
        print(f"   - Final groups: {len(final_groups)}")
        
        sizes = [len(g.functions) for g in final_groups]
        print(f"   - Group sizes: {sizes}")
        print(f"   - All ≤100? {'✅' if all(s <= 100 for s in sizes) else '❌'}")
        
        # Timing analysis
        print(f"\n⏱️  Timing Analysis:")
        print(f"   - Direct LLM call: {elapsed_llm:.1f}s")
        print(f"   - Full splitting: {elapsed_split:.1f}s")
        
        if elapsed_split > 5.0:
            print(f"   🎯 Slow enough to confirm actual LLM usage")
        elif elapsed_split > 1.0:
            print(f"   ⚠️  Moderate time - possibly mixed cache/LLM")
        else:
            print(f"   ⚠️  Very fast - likely used cache despite cleanup")
        
        return True
        
    except Exception as e:
        print(f"❌ Splitting failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print(f"\n⏰ End time: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 50)


if __name__ == "__main__":
    success = asyncio.run(test_force_llm_call())
    if success:
        print("🎯 Forced LLM test completed successfully")
    else:
        print("❌ Forced LLM test failed")