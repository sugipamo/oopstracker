#!/usr/bin/env python3
"""Test simple JSON prompt format."""

import json
import asyncio
import aiohttp

async def test_simple_json():
    url = "http://192.168.10.180:8000/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    # Different prompt styles
    prompts = [
        {
            "name": "Template Fill",
            "system": "Fill in the JSON template with your analysis. Output only the completed JSON.",
            "user": """Compare: def add(a,b): return a+b VS def sum_two(x,y): return x+y

{"similarity": ?, "confidence": ?, "reasoning": "?"}"""
        },
        {
            "name": "Complete JSON",
            "system": "Complete this JSON object with your code analysis. No other text.",
            "user": """Analyze: def add(a,b): return a+b VS def sum_two(x,y): return x+y

{"similarity":"""
        },
        {
            "name": "Direct JSON",
            "system": "You output JSON only. Format: {key:value}",
            "user": """Code comparison result as JSON:
Function 1: def add(a,b): return a+b
Function 2: def sum_two(x,y): return x+y
Keys: similarity(0-1), confidence(0-1), reasoning(text)"""
        }
    ]
    
    for prompt_info in prompts:
        print(f"\n{'='*60}")
        print(f"Testing: {prompt_info['name']}")
        print(f"{'='*60}")
        
        data = {
            "model": "/home/img-sorter/llm/models/llama-2-7b-chat.Q4_0.gguf",
            "messages": [
                {"role": "system", "content": prompt_info['system']},
                {"role": "user", "content": prompt_info['user']}
            ],
            "max_tokens": 150,
            "temperature": 0.0  # Zero temperature for deterministic output
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    
                    print(f"Response: {repr(content[:200])}")
                    
                    # Try to extract and parse JSON
                    # Method 1: Direct parse
                    try:
                        parsed = json.loads(content.strip())
                        print("✓ Direct parse SUCCESS")
                        print(f"Result: {parsed}")
                    except:
                        print("✗ Direct parse failed")
                        
                        # Method 2: Find first { and last }
                        start = content.find('{')
                        end = content.rfind('}')
                        if start >= 0 and end > start:
                            try:
                                json_str = content[start:end+1]
                                parsed = json.loads(json_str)
                                print("✓ Extracted JSON SUCCESS")
                                print(f"Result: {parsed}")
                            except Exception as e:
                                print(f"✗ Extracted JSON failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple_json())