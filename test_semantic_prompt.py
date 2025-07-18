#\!/usr/bin/env python3
"""Test semantic analysis prompt with Ollama."""

import json
import asyncio
import aiohttp

async def test_semantic_prompt():
    url = "http://192.168.10.180:8000/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    # Semantic analysis prompt
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
    
    data = {
        "model": "/home/img-sorter/llm/models/llama-2-7b-chat.Q4_0.gguf",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200,
        "temperature": 0.3
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            print(f"Status: {response.status}")
            
            text = await response.text()
            try:
                json_data = json.loads(text)
                if 'choices' in json_data and len(json_data['choices']) > 0:
                    content = json_data['choices'][0]['message']['content']
                    print(f"\nLLM Response:\n{content}")
                    
                    # Try to extract JSON from response
                    import re
                    json_pattern = r'\{[^{}]*"similarity"[^{}]*"confidence"[^{}]*"reasoning"[^{}]*\}'
                    json_matches = list(re.finditer(json_pattern, content, re.DOTALL))
                    
                    if json_matches:
                        print(f"\nFound {len(json_matches)} JSON matches")
                        for match in json_matches:
                            print(f"Match: {match.group(0)}")
                    else:
                        print("\nNo JSON found in response")
                        
            except Exception as e:
                print(f"\nError: {e}")

if __name__ == "__main__":
    asyncio.run(test_semantic_prompt())
