#!/usr/bin/env python3
"""Test ultra-simple formats for low-performance LLMs."""

import asyncio
import aiohttp
import re

async def test_simple_formats():
    url = "http://192.168.10.180:8000/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    formats = [
        {
            "name": "Single Line Score",
            "prompt": """Rate similarity of add(a,b) and sum_two(x,y) from 0-10: """,
            "parser": lambda text: {
                "similarity": float(re.search(r'(\d+)', text).group(1)) / 10,
                "confidence": 0.7,  # Fixed confidence
                "reasoning": "Functions perform similar addition operation"
            }
        },
        {
            "name": "Yes/No Question",
            "prompt": """Are these functions similar?
def add(a,b): return a+b
def sum_two(x,y): return x+y

Answer: YES or NO""",
            "parser": lambda text: {
                "similarity": 0.9 if 'YES' in text.upper() else 0.1,
                "confidence": 0.8,
                "reasoning": "Based on YES/NO answer"
            }
        },
        {
            "name": "Multiple Choice",
            "prompt": """How similar are these functions?
F1: def add(a,b): return a+b  
F2: def sum_two(x,y): return x+y

Choose: A)Very similar B)Somewhat similar C)Not similar""",
            "parser": lambda text: {
                "similarity": {"A": 0.9, "B": 0.5, "C": 0.1}.get(
                    re.search(r'([ABC])', text.upper()).group(1) if re.search(r'([ABC])', text.upper()) else 'B', 0.5
                ),
                "confidence": 0.8,
                "reasoning": "Based on multiple choice selection"
            }
        },
        {
            "name": "Fill in Blank",
            "prompt": """Complete: The functions add() and sum_two() are ___ similar (very/somewhat/not)""",
            "parser": lambda text: {
                "similarity": {"VERY": 0.9, "SOMEWHAT": 0.5, "NOT": 0.1}.get(
                    re.search(r'(very|somewhat|not)', text, re.I).group(1).upper() if re.search(r'(very|somewhat|not)', text, re.I) else "SOMEWHAT", 0.5
                ),
                "confidence": 0.8,
                "reasoning": "Based on similarity level"
            }
        },
        {
            "name": "Percentage Only",
            "prompt": """Similarity percentage between add(a,b) and sum_two(x,y): ____%""",
            "parser": lambda text: {
                "similarity": float(re.search(r'(\d+)%', text).group(1)) / 100 if re.search(r'(\d+)%', text) else 0.5,
                "confidence": 0.8,
                "reasoning": "Direct percentage estimate"
            }
        }
    ]
    
    success_count = 0
    
    for fmt in formats:
        print(f"\n{'='*60}")
        print(f"Testing: {fmt['name']}")
        print(f"{'='*60}")
        
        data = {
            "model": "/home/img-sorter/llm/models/llama-2-7b-chat.Q4_0.gguf",
            "messages": [
                {"role": "system", "content": "Answer concisely. Follow the format exactly."},
                {"role": "user", "content": fmt['prompt']}
            ],
            "max_tokens": 50,
            "temperature": 0.1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    
                    print(f"Response: {content.strip()}")
                    
                    try:
                        parsed = fmt['parser'](content)
                        print(f"✓ Parsed: similarity={parsed['similarity']:.2f}")
                        success_count += 1
                    except Exception as e:
                        print(f"✗ Failed: {e}")
    
    print(f"\n{'='*60}")
    print(f"Success rate: {success_count}/{len(formats)}")

if __name__ == "__main__":
    asyncio.run(test_simple_formats())