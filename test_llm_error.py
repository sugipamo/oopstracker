#!/usr/bin/env python3
"""Test script to reproduce and diagnose LLMResponseError."""

import ast
import json
import re
from typing import Dict, Any

def test_code_syntax(code: str) -> Dict[str, Any]:
    """Test if code has syntax errors."""
    try:
        ast.parse(code)
        return {"valid": True, "error": None}
    except SyntaxError as e:
        return {
            "valid": False,
            "error": str(e),
            "line": e.lineno,
            "offset": e.offset,
            "text": e.text
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}

def test_json_extraction(response: str) -> Dict[str, Any]:
    """Test JSON extraction from response."""
    # Try the same regex used in the code
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        try:
            data = json.loads(json_str)
            return {"success": True, "data": data}
        except json.JSONDecodeError as e:
            return {"success": False, "error": str(e), "json_str": json_str[:100]}
    else:
        return {"success": False, "error": "No JSON found in response"}

# Test cases
test_cases = [
    # Case 1: Code with unexpected indent
    {
        "name": "Unexpected Indent",
        "code": """def hello():
    print("Hello")
        print("World")  # This line has unexpected indent
""",
    },
    # Case 2: Mixed tabs and spaces
    {
        "name": "Mixed Indentation",
        "code": """def hello():
    print("Hello")  # spaces
	print("World")  # tab
""",
    },
    # Case 3: Valid code
    {
        "name": "Valid Code",
        "code": """def hello():
    print("Hello")
    print("World")
""",
    }
]

# Test prompt building
def build_test_prompt(code1: str, code2: str) -> str:
    """Build the same prompt used in semantic_analyzer."""
    return f"""以下の2つのコードの意味的な類似性を分析してください。

コード1:
```python
{code1}
```

コード2:
```python
{code2}
```

以下の基準で分析してください：
1. 機能的な類似性（同じことを実行しているか）
2. 意図的な類似性（同じ目的を持っているか）
3. 実装パターンの類似性（同じアプローチを使用しているか）

以下のJSON形式で回答してください：
{{
  "similarity": 0.85,
  "confidence": 0.9,
  "reasoning": "両方のコードは同じ機能を実装しているが、異なる実装方法を使用している。変数名や処理フローが異なるが、最終的な結果は同じ。",
  "details": {{
    "functional_similarity": 0.9,
    "intent_similarity": 0.8,
    "implementation_similarity": 0.7
  }}
}}

注意：
- similarity: 0.0-1.0の範囲で意味的類似度を評価
- confidence: 0.0-1.0の範囲で分析の信頼度を評価
- reasoning: 判定理由を日本語で説明
"""

# Test sample responses
sample_responses = [
    # Good response
    {
        "name": "Valid JSON Response",
        "response": """Here is my analysis:
{
  "similarity": 0.85,
  "confidence": 0.9,
  "reasoning": "両方のコードは同じ機能を実装している",
  "details": {
    "functional_similarity": 0.9,
    "intent_similarity": 0.8,
    "implementation_similarity": 0.7
  }
}
""",
    },
    # Response with multiple JSON objects
    {
        "name": "Multiple JSON Objects",
        "response": """First analysis: {"test": 1}
Real analysis:
{
  "similarity": 0.85,
  "confidence": 0.9,
  "reasoning": "両方のコードは同じ機能を実装している"
}
Another object: {"test": 2}
""",
    },
    # Malformed JSON
    {
        "name": "Malformed JSON",
        "response": """Analysis result:
{
  "similarity": 0.85,
  "confidence": 0.9,
  "reasoning": "両方のコードは同じ機能を実装している"
  // Missing closing brace
""",
    }
]

def main():
    print("=== Testing Code Syntax ===")
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        result = test_code_syntax(test['code'])
        print(f"Result: {result}")
    
    print("\n=== Testing JSON Extraction ===")
    for test in sample_responses:
        print(f"\nTest: {test['name']}")
        result = test_json_extraction(test['response'])
        print(f"Result: {result}")
    
    print("\n=== Testing Prompt Building ===")
    # Test with problematic code
    prompt = build_test_prompt(test_cases[0]['code'], test_cases[2]['code'])
    print("Prompt preview (first 500 chars):")
    print(prompt[:500])
    print("...")
    
    # Check if the prompt itself is valid
    print("\n=== Checking Prompt Validity ===")
    try:
        # Try to parse the prompt as JSON (it shouldn't work since it's not pure JSON)
        json.loads(prompt)
        print("ERROR: Prompt parsed as JSON (shouldn't happen)")
    except json.JSONDecodeError:
        print("OK: Prompt is not valid JSON (expected)")
    
    # Check if code blocks are properly formatted
    code_block_pattern = r'```python\n(.*?)\n```'
    matches = re.findall(code_block_pattern, prompt, re.DOTALL)
    print(f"\nFound {len(matches)} code blocks in prompt")
    for i, code in enumerate(matches):
        print(f"\nCode block {i+1} syntax check:")
        result = test_code_syntax(code)
        print(f"Result: {result}")

if __name__ == "__main__":
    main()