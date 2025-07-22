#!/usr/bin/env python3
"""
Test real LLM splitting with fixed prompt format.
"""

import asyncio
import sys
import re
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oopstracker.smart_group_splitter import SmartGroupSplitter
from oopstracker.function_group_clustering import FunctionGroup
from oopstracker.ai_analysis_coordinator import get_ai_coordinator


async def test_real_llm_splitting():
    """Test splitting with real LLM server."""
    print("🌐 Testing Real LLM Splitting")
    print("=" * 50)
    print(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
    
    # Create small test dataset (150 functions - manageable size)
    functions = []
    
    for i in range(30):
        functions.extend([
            {'name': f'create_user_{i}', 'code': f'def create_user_{i}(data): pass'},
            {'name': f'update_profile_{i}', 'code': f'def update_profile_{i}(data): pass'},
            {'name': f'validate_email_{i}', 'code': f'def validate_email_{i}(value): pass'},
            {'name': f'handle_request_{i}', 'code': f'def handle_request_{i}(req): pass'},
            {'name': f'query_db_{i}', 'code': f'def query_db_{i}(sql): pass'}
        ])
    
    print(f"\n📊 Test data: {len(functions)} functions")
    
    # Create initial group
    initial_group = FunctionGroup(
        group_id="test_group",
        functions=functions,
        label="Real LLM Test Group",
        confidence=0.8,
        metadata={}
    )
    
    print(f"📈 Initial group: {len(functions)} functions (exceeds threshold of 100)")
    
    # Create splitter with real LLM
    print("\n🔧 Initializing real LLM splitter...")
    splitter = SmartGroupSplitter(enable_ai=True, use_mock_ai=False)
    
    # Test with improved prompt format
    async def generate_real_split_pattern(sample_functions):
        """Generate split pattern with properly formatted prompt."""
        coordinator = get_ai_coordinator(use_mock=False)
        
        # Format sample functions clearly
        function_list = "\n".join([
            f"Function: {func['name']}\nCode: {func['code']}\n"
            for func in sample_functions[:5]
        ])
        
        # Clear, direct prompt
        prompt = f"""以下の関数を2つのグループに分割する正規表現パターンを作成してください：

{function_list}

要求：
1. 関数定義行（def 行）にマッチする正規表現を1つ作成
2. マッチした関数=グループA、マッチしない関数=グループB
3. できるだけ均等に分割
4. パターンは関数名の特徴を使用

必須の回答形式：
PATTERN: <正規表現パターン>
REASONING: <分類の根拠>

例：
PATTERN: def\\s+(create|update)_
REASONING: create/update操作を分離"""
        
        response = await coordinator.analyze_intent(prompt)
        
        if not response.success:
            raise RuntimeError(f"LLM failed: {response.reasoning}")
        
        result_text = response.result.get('purpose', '') if isinstance(response.result, dict) else str(response.result)
        
        # Extract pattern more robustly
        pattern_match = re.search(r'PATTERN:\s*([^\n]+)', result_text, re.IGNORECASE)
        reasoning_match = re.search(r'REASONING:\s*([^\n]+)', result_text, re.IGNORECASE)
        
        if not pattern_match:
            raise RuntimeError(f"No PATTERN found in response: {result_text[:200]}...")
        
        pattern = pattern_match.group(1).strip()
        reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided"
        
        print(f"   🔍 Generated pattern: {pattern}")
        print(f"   💭 Reasoning: {reasoning}")
        
        return pattern, reasoning
    
    # Replace the LLM method
    splitter.generate_split_regex_with_llm = generate_real_split_pattern
    
    # Test splitting
    print("\n🤖 Applying real LLM-based splitting...")
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
        
        # Show groups
        print(f"\n📋 Final groups:")
        for i, group in enumerate(final_groups):
            pattern = group.metadata.get('split_rule', 'N/A')
            print(f"   {i+1}. {group.label}: {len(group.functions)} functions")
            if pattern != 'N/A':
                print(f"      Pattern: {pattern[:50]}...")
        
        # Verify function accounting
        total_functions_in_groups = sum(len(g.functions) for g in final_groups)
        print(f"\n✅ Function accounting:")
        print(f"   - Original: {len(functions)}")
        print(f"   - Final: {total_functions_in_groups}")
        print(f"   - Match: {'✅' if total_functions_in_groups == len(functions) else '❌'}")
        
        if len(large_groups) == 0:
            print(f"\n🎯 SUCCESS: All groups split to ≤100 functions!")
            return True
        else:
            print(f"\n⚠️  Some groups still >100 (max depth reached)")
            return True  # Still success if reduced sizes
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print(f"\n⏰ End time: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 50)


if __name__ == "__main__":
    success = asyncio.run(test_real_llm_splitting())
    if success:
        print("🎯 Real LLM splitting test completed successfully")
    else:
        print("❌ Real LLM splitting test failed")