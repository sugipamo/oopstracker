#!/usr/bin/env python3
"""
Test direct HTTP connection to LLM server.
"""

import aiohttp
import asyncio
import json
import time


async def test_direct_http():
    """Test direct HTTP connection."""
    print("🌐 Testing Direct HTTP Connection")
    print("=" * 40)
    
    url = "http://192.168.10.180:8000/v1/chat/completions"
    payload = {
        "model": "/home/img-sorter/llm/models/llama-2-7b-chat.Q4_0.gguf",
        "messages": [{"role": "user", "content": "Hello, respond briefly"}],
        "max_tokens": 10
    }
    
    print(f"📤 Sending request to: {url}")
    
    start_time = time.time()
    try:
        timeout = aiohttp.ClientTimeout(total=15)  # 15 second timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as response:
                elapsed = time.time() - start_time
                
                print(f"✅ Response received in {elapsed:.2f} seconds")
                print(f"   Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    content = data['choices'][0]['message']['content']
                    print(f"   Content: {content}")
                    return True
                else:
                    text = await response.text()
                    print(f"   Error response: {text}")
                    return False
    
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"❌ Timeout after {elapsed:.2f} seconds")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Error after {elapsed:.2f} seconds: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_direct_http())
    if success:
        print("\n🎯 Direct HTTP connection successful!")
    else:
        print("\n❌ Direct HTTP connection failed")