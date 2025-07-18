#!/usr/bin/env python3
"""Test LLM provider directly to capture actual error."""

import asyncio
import sys
sys.path.insert(0, '/home/coding/code-smith/util/llm-providers/src')

from llm_providers import create_provider, LLMConfig

async def test_llm_provider():
    # Create LLM config
    llm_config = LLMConfig(
        provider="llama",
        base_url="http://192.168.10.180:8000/v1/chat/completions",
        model="/home/img-sorter/llm/models/llama-2-7b-chat.Q4_0.gguf",
        temperature=0.3,
        max_tokens=1000,
        timeout=60.0
    )
    
    # Create provider
    provider = await create_provider(llm_config)
    
    # Simple test prompt
    prompt = """以下の2つのコードの意味的な類似性を分析してください。

コード1:
```python
def add(a, b):
    return a + b
```

コード2:
```python
def sum_two(x, y):
    return x + y
```

以下のJSON形式で回答してください：
{
  "similarity": 0.85,
  "confidence": 0.9,
  "reasoning": "両方のコードは同じ機能を実装している"
}"""
    
    try:
        # Generate response
        response = await provider.generate(prompt)
        print(f"Success! Response: {response.content[:200]}...")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        await provider.cleanup()

if __name__ == "__main__":
    asyncio.run(test_llm_provider())