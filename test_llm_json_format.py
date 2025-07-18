#!/usr/bin/env python3
"""Test LLM response format to understand JSON parsing issues."""

import json
import asyncio
import aiohttp

async def test_llm_json_format():
    url = "http://192.168.10.180:8000/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    # Refined prompt to get clean JSON response
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

回答は次のJSON形式のみで、他の説明は不要です：
{"similarity": 0.85, "confidence": 0.9, "reasoning": "両方のコードは同じ機能を実装している"}"""
    
    data = {
        "model": "/home/img-sorter/llm/models/llama-2-7b-chat.Q4_0.gguf",
        "messages": [
            {"role": "system", "content": "あなたはコード分析の専門家です。指定されたJSON形式で回答してください。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 200,
        "temperature": 0.3
    }
    
    print("Sending request to LLM...")
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            print(f"Status: {response.status}")
            
            text = await response.text()
            try:
                json_data = json.loads(text)
                if 'choices' in json_data and len(json_data['choices']) > 0:
                    content = json_data['choices'][0]['message']['content']
                    print(f"\nLLM Response:\n{content}")
                    print(f"\nResponse length: {len(content)} chars")
                    
                    # Try to extract JSON from response
                    print("\n--- JSON Extraction Test ---")
                    
                    # Method 1: Direct parse
                    try:
                        parsed = json.loads(content.strip())
                        print(f"Direct parse SUCCESS: {parsed}")
                    except json.JSONDecodeError as e:
                        print(f"Direct parse failed: {e}")
                    
                    # Method 2: Find JSON with brackets
                    stack = []
                    json_start = -1
                    json_candidates = []
                    
                    for i, char in enumerate(content):
                        if char == '{':
                            if not stack:
                                json_start = i
                            stack.append('{')
                        elif char == '}' and stack:
                            stack.pop()
                            if not stack and json_start != -1:
                                json_candidates.append(content[json_start:i+1])
                                json_start = -1
                    
                    print(f"\nFound {len(json_candidates)} JSON candidates")
                    for idx, candidate in enumerate(json_candidates):
                        try:
                            parsed = json.loads(candidate)
                            print(f"Candidate {idx+1} SUCCESS: {parsed}")
                        except json.JSONDecodeError as e:
                            print(f"Candidate {idx+1} failed: {e}")
                            print(f"  Content: {candidate[:100]}...")
                    
            except Exception as e:
                print(f"\nError: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm_json_format())