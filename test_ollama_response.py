#\!/usr/bin/env python3
"""Test Ollama API response format."""

import json
import asyncio
import aiohttp

async def test_ollama():
    url = "http://192.168.10.180:8000/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    # Simple test prompt
    data = {
        "model": "/home/img-sorter/llm/models/llama-2-7b-chat.Q4_0.gguf",
        "messages": [{"role": "user", "content": "Reply with just: hello"}],
        "max_tokens": 10,
        "temperature": 0.1
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            print(f"Status: {response.status}")
            print(f"Headers: {dict(response.headers)}")
            
            text = await response.text()
            print(f"\nRaw response:\n{text}")
            
            try:
                json_data = json.loads(text)
                print(f"\nParsed JSON:\n{json.dumps(json_data, indent=2)}")
                
                # Check expected fields
                if 'choices' in json_data:
                    print("\n✓ Has 'choices' field")
                    if len(json_data['choices']) > 0:
                        choice = json_data['choices'][0]
                        if 'message' in choice:
                            print("✓ Has 'message' field")
                            print(f"Content: {choice['message'].get('content', 'N/A')}")
                        else:
                            print("✗ Missing 'message' field")
                else:
                    print("\n✗ Missing 'choices' field")
                    
            except json.JSONDecodeError as e:
                print(f"\nJSON parse error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ollama())
