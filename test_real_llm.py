#!/usr/bin/env python3
"""
Test with real LLM server.
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oopstracker.ai_analysis_coordinator import get_ai_coordinator


async def test_real_llm_connection():
    """Test connection to real LLM server."""
    print("🌐 Testing Real LLM Connection")
    print("=" * 50)
    print(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
    
    # Get real LLM coordinator (not mock)
    print("\n🔧 Initializing real LLM coordinator...")
    try:
        coordinator = get_ai_coordinator(use_mock=False)
        print("✅ Coordinator created")
        print(f"   Available: {coordinator.available}")
    except Exception as e:
        print(f"❌ Failed to create coordinator: {e}")
        return
    
    # Test simple intent analysis
    print("\n📤 Testing simple LLM call...")
    simple_prompt = "Hello, please respond with a simple greeting."
    
    start_time = time.time()
    try:
        response = await asyncio.wait_for(
            coordinator.analyze_intent(simple_prompt),
            timeout=30.0  # 30 second timeout
        )
        elapsed = time.time() - start_time
        
        print(f"✅ Response received in {elapsed:.2f} seconds")
        print(f"   Success: {response.success}")
        print(f"   Result: {response.result}")
        
        if not response.success:
            print(f"   Reasoning: {response.reasoning}")
            return False
        
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"❌ Timeout after {elapsed:.2f} seconds")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Error after {elapsed:.2f} seconds: {e}")
        return False
    
    # Test pattern generation
    print("\n📤 Testing pattern generation...")
    pattern_prompt = """以下の3個の関数を2つのグループに分割する正規表現を作成してください。

Function: create_user_0
Code:
def create_user_0(data): pass

Function: validate_email_1  
Code:
def validate_email_1(value): pass

Function: handle_get_order_2
Code:
def handle_get_order_2(request): pass

要求：
1. 1つの正規表現パターン（関数の内容に対して適用）
2. マッチした関数=グループA、マッチしない関数=グループB
3. できるだけ均等に分割
4. 分類の根拠も説明

回答形式：
PATTERN: <正規表現>
REASONING: <分類理由>
"""
    
    start_time = time.time()
    try:
        response = await asyncio.wait_for(
            coordinator.analyze_intent(pattern_prompt),
            timeout=60.0  # 60 second timeout for pattern generation
        )
        elapsed = time.time() - start_time
        
        print(f"✅ Pattern response received in {elapsed:.2f} seconds")
        print(f"   Success: {response.success}")
        
        if response.success:
            result_text = response.result.get('purpose', '') if isinstance(response.result, dict) else str(response.result)
            print(f"   Response preview: {result_text[:200]}...")
            
            # Try to extract pattern
            import re
            pattern_match = re.search(r'PATTERN:\s*(.+)', result_text, re.IGNORECASE)
            if pattern_match:
                pattern = pattern_match.group(1).strip()
                print(f"   Extracted pattern: {pattern}")
                return True
            else:
                print("   ⚠️  No PATTERN found in response")
        else:
            print(f"   Reasoning: {response.reasoning}")
        
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"❌ Pattern generation timeout after {elapsed:.2f} seconds")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Pattern generation error after {elapsed:.2f} seconds: {e}")
        return False
    
    print(f"\n⏰ End time: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_real_llm_connection())
    if success:
        print("🎯 Real LLM connection successful - ready for splitting test")
    else:
        print("❌ Real LLM connection failed - check server configuration")