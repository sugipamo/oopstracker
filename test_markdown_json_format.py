#!/usr/bin/env python3
"""Test markdown-embedded JSON format for LLM responses."""

import json
import asyncio
import aiohttp
import re

async def test_markdown_json():
    url = "http://192.168.10.180:8000/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    prompt = """Analyze code similarity between two functions.

Code 1: def add(a, b): return a + b
Code 2: def sum_two(x, y): return x + y

Analyze based on:
1. Functional similarity (do they perform the same task?)
2. Intent similarity (do they have the same purpose?)
3. Implementation similarity (do they use the same approach?)

Provide your analysis in markdown with embedded JSON:

```json
{"similarity":0.85,"confidence":0.9,"reasoning":"両方の関数は同じタスクを実行する","details":{"functional_similarity":0.9,"intent_similarity":0.8,"implementation_similarity":0.7}}
```"""
    
    data = {
        "model": "/home/img-sorter/llm/models/llama-2-7b-chat.Q4_0.gguf",
        "messages": [
            {"role": "system", "content": "You are a code similarity analyzer. Always format your response as markdown with a JSON code block containing the analysis results."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300,
        "temperature": 0.1
    }
    
    print("Sending request to LLM...")
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                content = result['choices'][0]['message']['content']
                
                print(f"Raw response:\n{content}\n")
                print(f"Length: {len(content)} chars\n")
                
                # Extract JSON from markdown
                json_pattern = r'```json\s*\n?(.*?)\n?```'
                json_matches = re.findall(json_pattern, content, re.DOTALL)
                
                if json_matches:
                    print(f"Found {len(json_matches)} JSON blocks")
                    for i, json_str in enumerate(json_matches):
                        try:
                            parsed = json.loads(json_str.strip())
                            print(f"✓ JSON block {i+1} parsed successfully:")
                            print(json.dumps(parsed, indent=2, ensure_ascii=False))
                        except json.JSONDecodeError as e:
                            print(f"✗ JSON block {i+1} failed: {e}")
                            print(f"Content: {json_str[:100]}...")
                else:
                    print("✗ No JSON blocks found in markdown")

if __name__ == "__main__":
    asyncio.run(test_markdown_json())