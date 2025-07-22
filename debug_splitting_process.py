#!/usr/bin/env python3
"""
Debug the splitting process step by step.
"""

import asyncio
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oopstracker.smart_group_splitter import SmartGroupSplitter
from oopstracker.function_group_clustering import FunctionGroup
from oopstracker.ai_analysis_coordinator import get_ai_coordinator


async def debug_splitting():
    """Debug the splitting process step by step."""
    print("🔍 Debugging LLM Splitting Process")
    print("=" * 50)
    
    # Create test functions with clear patterns
    functions = [
        {'name': 'create_user_0', 'code': 'def create_user_0(data): pass'},
        {'name': 'create_user_1', 'code': 'def create_user_1(data): pass'},
        {'name': 'validate_email_0', 'code': 'def validate_email_0(value): pass'},
        {'name': 'validate_email_1', 'code': 'def validate_email_1(value): pass'},
        {'name': 'handle_get_order_0', 'code': 'def handle_get_order_0(request): pass'},
        {'name': 'handle_get_order_1', 'code': 'def handle_get_order_1(request): pass'},
    ]
    
    # Create test group
    group = FunctionGroup(
        group_id="debug_group",
        functions=functions,
        label="Debug Group",
        confidence=0.8,
        metadata={}
    )
    
    print(f"📊 Test Group: {len(functions)} functions")
    for func in functions:
        print(f"   - {func['name']}")
    
    # Initialize coordinator and splitter
    coordinator = get_ai_coordinator(use_mock=True)
    splitter = SmartGroupSplitter(enable_ai=True, use_mock_ai=True)
    
    # Step 1: Generate pattern with LLM
    print("\n🤖 Step 1: Generate pattern with LLM")
    sample_functions = functions[:3]  # Take 3 functions as sample
    
    pattern, reasoning = await splitter.generate_split_regex_with_llm(sample_functions)
    print(f"   Generated pattern: {pattern}")
    print(f"   Reasoning: {reasoning}")
    
    # Step 2: Test pattern manually
    print("\n🧪 Step 2: Test pattern against all functions")
    matches = []
    no_matches = []
    
    for func in functions:
        if re.search(pattern, func['code']):
            matches.append(func)
        else:
            no_matches.append(func)
    
    print(f"   Matches ({len(matches)}):")
    for func in matches:
        print(f"     ✅ {func['name']}")
    
    print(f"   No matches ({len(no_matches)}):")
    for func in no_matches:
        print(f"     ❌ {func['name']}")
    
    # Step 3: Validate split
    print("\n✅ Step 3: Validate split")
    is_valid, matched, unmatched = splitter.validate_split(group, pattern)
    print(f"   Valid split: {is_valid}")
    print(f"   Matched: {len(matched)} functions")
    print(f"   Unmatched: {len(unmatched)} functions")
    
    if is_valid:
        print("   ✅ Split would be accepted")
    else:
        print("   ❌ Split would be rejected")
        # Show why
        if len(matched) == 0 or len(unmatched) == 0:
            print("   Reason: One group would be empty")
        elif abs(len(matched) - len(unmatched)) > len(functions) * 0.8:
            print("   Reason: Groups too unbalanced")
    
    # Step 4: Try actual splitting
    print("\n🔄 Step 4: Try actual splitting")
    try:
        result_groups = await splitter.split_large_groups_with_llm([group], max_depth=1)
        print(f"   Result: {len(result_groups)} groups created")
        for i, g in enumerate(result_groups):
            print(f"   Group {i+1}: {len(g.functions)} functions - {g.label}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("💡 Analysis:")
    print("   - LLM call succeeds")
    print("   - Pattern generation works")
    print("   - Issue may be in pattern effectiveness or validation")


if __name__ == "__main__":
    asyncio.run(debug_splitting())