#!/usr/bin/env python3
"""
Compare direct HTTP request with llm-providers request to find differences.
"""

import aiohttp
import asyncio
import json
import logging
from llm_providers import create_provider, LLMConfig

# Enable debug logging to see what llm-providers sends
logging.basicConfig(level=logging.DEBUG)

async def test_direct_http():
    """Test direct HTTP (this works)."""
    print("\n🔵 Testing Direct HTTP (Working)")
    print("=" * 50)
    
    url = "http://192.168.10.180:8000/v1/chat/completions"
    payload = {
        "model": "/home/img-sorter/llm/models/llama-2-7b-chat.Q4_0.gguf",
        "messages": [{"role": "user", "content": "Hello, respond briefly"}],
        "max_tokens": 10
    }
    
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"Response: {data}")
                else:
                    text = await response.text()
                    print(f"Error: {text}")
    except Exception as e:
        print(f"Exception: {e}")


async def test_llm_providers():
    """Test with llm-providers (this fails)."""
    print("\n🔴 Testing llm-providers")
    print("=" * 50)
    
    # Configure exactly as in ai_analysis_coordinator.py
    config = LLMConfig(
        provider="llama",
        model="/home/img-sorter/llm/models/llama-2-7b-chat.Q4_0.gguf",
        base_url="http://192.168.10.180:8000/v1/chat/completions",
        temperature=0.1,
        max_tokens=10,
        timeout=15.0,
        retry_count=1,
        retry_delay=0.5
    )
    
    print(f"Config: provider={config.provider}, model={config.model}")
    print(f"base_url={config.base_url}")
    
    try:
        provider = await create_provider(config)
        response = await provider.generate("Hello, respond briefly")
        print(f"Response: {response}")
        await provider.cleanup()
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run both tests."""
    await test_direct_http()
    await test_llm_providers()


if __name__ == "__main__":
    asyncio.run(main())