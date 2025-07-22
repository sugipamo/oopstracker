#!/usr/bin/env python3
"""
Debug LLM initialization process.
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set environment variables for debugging
os.environ['LLM_TIMEOUT'] = '10'  # Short timeout for testing

async def debug_llm_init():
    """Debug the LLM initialization step by step."""
    print("🔍 Debugging LLM Initialization")
    print("=" * 50)
    
    print("\n📋 Environment Variables:")
    llm_vars = ['LLM_API_URL', 'LLM_MODEL', 'LLM_TIMEOUT', 'LLM_RETRY_COUNT']
    for var in llm_vars:
        value = os.getenv(var, 'Not set')
        print(f"   {var}: {value}")
    
    print("\n🔧 Step 1: Import modules...")
    try:
        from oopstracker.ai_analysis_coordinator import AIAnalysisCoordinator
        print("✅ Modules imported successfully")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return
    
    print("\n🔧 Step 2: Create coordinator...")
    try:
        coordinator = AIAnalysisCoordinator()
        print("✅ Coordinator object created")
        print(f"   Available: {coordinator.available}")
    except Exception as e:
        print(f"❌ Coordinator creation failed: {e}")
        return
    
    print("\n🔧 Step 3: Test simple call with short timeout...")
    try:
        response = await asyncio.wait_for(
            coordinator.analyze_intent("test"),
            timeout=15.0
        )
        print(f"✅ Call completed")
        print(f"   Success: {response.success}")
        if not response.success:
            print(f"   Reasoning: {response.reasoning}")
    except asyncio.TimeoutError:
        print("❌ Timeout during call")
    except Exception as e:
        print(f"❌ Error during call: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_llm_init())