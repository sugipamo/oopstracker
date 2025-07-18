#!/usr/bin/env python3
"""Test alternative output formats that are easier for LLMs."""

import asyncio
import aiohttp
import re

async def test_formats():
    url = "http://192.168.10.180:8000/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    formats = [
        {
            "name": "Simple Score Format",
            "prompt": """Compare these functions:
F1: def add(a,b): return a+b
F2: def sum_two(x,y): return x+y

Answer with:
SIMILARITY: (0-100)
CONFIDENCE: (0-100)
REASON: (one line explanation)""",
            "parser": lambda text: {
                "similarity": float(re.search(r'SIMILARITY:\s*(\d+)', text).group(1)) / 100,
                "confidence": float(re.search(r'CONFIDENCE:\s*(\d+)', text).group(1)) / 100,
                "reasoning": re.search(r'REASON:\s*(.+)', text).group(1).strip()
            }
        },
        {
            "name": "Natural Language with Numbers",
            "prompt": """Compare: def add(a,b): return a+b VS def sum_two(x,y): return x+y

Rate similarity from 0 to 10.
How confident are you from 0 to 10?
Why? (short answer)""",
            "parser": lambda text: {
                "similarity": float(re.search(r'(\d+)\s*(?:/10|out of 10)?', text).group(1)) / 10,
                "confidence": float(re.search(r'confident.*?(\d+)', text, re.I).group(1)) / 10,
                "reasoning": text.split('?')[-1].strip() if '?' in text else "No reason given"
            }
        },
        {
            "name": "Structured Text",
            "prompt": """Compare functions:
1) def add(a,b): return a+b
2) def sum_two(x,y): return x+y

Fill in:
Similar: YES/NO/PARTIAL
Score: 0-10
Because: ___""",
            "parser": lambda text: {
                "similarity": {"YES": 0.9, "NO": 0.1, "PARTIAL": 0.5}.get(
                    re.search(r'Similar:\s*(YES|NO|PARTIAL)', text, re.I).group(1).upper(), 0.5
                ),
                "confidence": float(re.search(r'Score:\s*(\d+)', text).group(1)) / 10,
                "reasoning": re.search(r'Because:\s*(.+)', text).group(1).strip()
            }
        },
        {
            "name": "CSV Style",
            "prompt": """Analyze code similarity. Output as CSV:
similarity,confidence,reasoning

Code 1: def add(a,b): return a+b
Code 2: def sum_two(x,y): return x+y""",
            "parser": lambda text: {
                parts: text.strip().split('\n')[-1].split(','),
                "similarity": float(parts[0]),
                "confidence": float(parts[1]),
                "reasoning": parts[2]
            } if (parts := None) else {}
        },
        {
            "name": "Key-Value Pairs",
            "prompt": """Compare: def add(a,b): return a+b VS def sum_two(x,y): return x+y

Output as key=value pairs:
sim=0.0-1.0
conf=0.0-1.0  
why=explanation""",
            "parser": lambda text: {
                "similarity": float(re.search(r'sim=(\d*\.?\d+)', text).group(1)),
                "confidence": float(re.search(r'conf=(\d*\.?\d+)', text).group(1)),
                "reasoning": re.search(r'why=(.+)', text).group(1).strip()
            }
        }
    ]
    
    for fmt in formats:
        print(f"\n{'='*60}")
        print(f"Testing: {fmt['name']}")
        print(f"{'='*60}")
        
        data = {
            "model": "/home/img-sorter/llm/models/llama-2-7b-chat.Q4_0.gguf",
            "messages": [
                {"role": "system", "content": "You are a code similarity analyzer. Follow the output format exactly."},
                {"role": "user", "content": fmt['prompt']}
            ],
            "max_tokens": 100,
            "temperature": 0.1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    
                    print(f"Response:\n{content}\n")
                    
                    try:
                        parsed = fmt['parser'](content)
                        print(f"✓ Parsed successfully: {parsed}")
                    except Exception as e:
                        print(f"✗ Parse failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_formats())