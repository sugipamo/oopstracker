#!/usr/bin/env python3
"""Analyze LLM responses to understand fallback patterns."""

import json
import asyncio
import aiohttp
import re

async def test_various_prompts():
    url = "http://192.168.10.180:8000/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    # Test different prompt styles
    prompts = [
        # Original prompt (problematic)
        {
            "name": "Original",
            "prompt": """以下の2つのコードの意味的な類似性を分析してください。

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

回答は以下のJSON形式のみで、他の説明は不要です。改行を入れずに1行で出力してください：
{"similarity": 0.85, "confidence": 0.9, "reasoning": "両方のコードは同じ機能を実装している", "details": {"functional_similarity": 0.9, "intent_similarity": 0.8, "implementation_similarity": 0.7}}"""
        },
        
        # Simplified prompt
        {
            "name": "Simplified",
            "prompt": """Compare these two Python functions and return ONLY a JSON object:

Function 1: def add(a, b): return a + b
Function 2: def sum_two(x, y): return x + y

Return JSON: {"similarity": 0.0-1.0, "confidence": 0.0-1.0, "reasoning": "explanation"}"""
        },
        
        # More explicit JSON-only prompt
        {
            "name": "JSON-Only",
            "prompt": """JSON出力のみ。説明文なし。改行なし。

コード比較:
1) def add(a, b): return a + b
2) def sum_two(x, y): return x + y

出力形式: {"similarity":数値,"confidence":数値,"reasoning":"説明"}

JSON:"""
        },
        
        # English prompt with strict format
        {
            "name": "English-Strict",
            "prompt": """Analyze code similarity. Output ONLY valid JSON on a single line.

Code 1: def add(a, b): return a + b
Code 2: def sum_two(x, y): return x + y

Required JSON format (no newlines):
{"similarity":0.85,"confidence":0.9,"reasoning":"Both implement addition"}

Your JSON response:"""
        }
    ]
    
    for prompt_info in prompts:
        print(f"\n{'='*60}")
        print(f"Testing: {prompt_info['name']}")
        print(f"{'='*60}")
        
        data = {
            "model": "/home/img-sorter/llm/models/llama-2-7b-chat.Q4_0.gguf",
            "messages": [
                {"role": "system", "content": "You are a code analysis expert. Always respond with valid JSON only."},
                {"role": "user", "content": prompt_info['prompt']}
            ],
            "max_tokens": 150,
            "temperature": 0.1  # Lower temperature for more consistent output
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    
                    print(f"Raw response: {repr(content)}")
                    print(f"Length: {len(content)} chars")
                    
                    # Try to parse as JSON
                    try:
                        parsed = json.loads(content.strip())
                        print("✓ Direct JSON parse SUCCESS")
                        print(f"Parsed: {parsed}")
                    except json.JSONDecodeError as e:
                        print(f"✗ Direct JSON parse failed: {e}")
                        
                        # Try to extract JSON
                        json_pattern = r'\{[^{}]*"similarity"[^{}]*"confidence"[^{}]*"reasoning"[^{}]*\}'
                        matches = re.findall(json_pattern, content, re.DOTALL)
                        
                        if matches:
                            print(f"Found {len(matches)} JSON candidates")
                            for i, match in enumerate(matches):
                                try:
                                    # Clean up newlines in the match
                                    cleaned = re.sub(r'[\r\n]+', ' ', match)
                                    parsed = json.loads(cleaned)
                                    print(f"✓ Extracted JSON {i+1} SUCCESS")
                                    print(f"Parsed: {parsed}")
                                except:
                                    print(f"✗ Extracted JSON {i+1} failed")
                        else:
                            print("✗ No JSON pattern found")

if __name__ == "__main__":
    asyncio.run(test_various_prompts())