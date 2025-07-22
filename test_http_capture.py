#!/usr/bin/env python3
"""
Capture the exact HTTP requests to compare differences.
"""

import aiohttp
import asyncio
import json
from llm_providers import create_provider, LLMConfig

# Create a custom connector to log requests
class LoggingConnector(aiohttp.TCPConnector):
    async def _create_connection(self, req, traces, timeout):
        print(f"\n📡 Outgoing Request:")
        print(f"   Method: {req.method}")
        print(f"   URL: {req.url}")
        print(f"   Headers: {dict(req.headers)}")
        if req.body:
            # Try to parse as JSON for pretty printing
            try:
                body_str = req.body._value.decode('utf-8') if hasattr(req.body, '_value') else str(req.body)
                body_json = json.loads(body_str)
                print(f"   Body: {json.dumps(body_json, indent=4)}")
            except:
                print(f"   Body: {req.body}")
        return await super()._create_connection(req, traces, timeout)


async def test_with_logging():
    """Test llm-providers with request logging."""
    print("🔍 Testing llm-providers with Request Logging")
    print("=" * 60)
    
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
    
    # Monkey patch to use our logging connector
    original_init = aiohttp.ClientSession.__init__
    
    def patched_init(self, *args, **kwargs):
        kwargs['connector'] = LoggingConnector()
        original_init(self, *args, **kwargs)
    
    aiohttp.ClientSession.__init__ = patched_init
    
    try:
        provider = await create_provider(config)
        response = await provider.generate("Hello, respond briefly")
        print(f"\n✅ Response: {response.content}")
        await provider.cleanup()
    except Exception as e:
        print(f"\n❌ Exception: {type(e).__name__}: {e}")
    finally:
        # Restore original
        aiohttp.ClientSession.__init__ = original_init


async def test_direct_with_logging():
    """Test direct HTTP with same logging."""
    print("\n🔍 Testing Direct HTTP with Request Logging")
    print("=" * 60)
    
    connector = LoggingConnector()
    timeout = aiohttp.ClientTimeout(total=15)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        url = "http://192.168.10.180:8000/v1/chat/completions"
        payload = {
            "model": "/home/img-sorter/llm/models/llama-2-7b-chat.Q4_0.gguf",
            "messages": [{"role": "user", "content": "Hello, respond briefly"}],
            "max_tokens": 10
        }
        
        try:
            async with session.post(url, json=payload) as response:
                data = await response.json()
                print(f"\n✅ Response: {data['choices'][0]['message']['content']}")
        except Exception as e:
            print(f"\n❌ Exception: {type(e).__name__}: {e}")


async def main():
    await test_direct_with_logging()
    await test_with_logging()


if __name__ == "__main__":
    asyncio.run(main())