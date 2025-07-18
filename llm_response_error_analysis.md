# LLMResponseError Root Cause Analysis

## Summary

The `LLMResponseError` is raised in the `llm_providers` module when there are issues with the LLM response. Based on the code analysis, here are the key findings:

## 1. Where LLMResponseError is Raised

The error is raised in `/home/coding/code-smith/util/llm-providers/src/llm_providers/llama.py`:

- **Line 81-83**: When HTTP response status is not 200
- **Line 89**: When response JSON is missing "choices" field
- **Line 93**: When response JSON is missing "message" field

## 2. Conditions That Trigger the Error

1. **HTTP Status Error**: Non-200 status code from the LLM API
2. **Invalid Response Format**: Missing required fields in JSON response
3. **Malformed JSON**: Though not directly shown, JSON parsing errors would also trigger this

## 3. The Exact Prompt Being Sent

From `semantic_analyzer.py` lines 218-251, the prompt template is:

```
以下の2つのコードの意味的な類似性を分析してください。

コード1:
```{code1.language}
{code1.code}
```

コード2:
```{code2.language}
{code2.code}
```

以下の基準で分析してください：
1. 機能的な類似性（同じことを実行しているか）
2. 意図的な類似性（同じ目的を持っているか）
3. 実装パターンの類似性（同じアプローチを使用しているか）

以下のJSON形式で回答してください：
{
  "similarity": 0.85,
  "confidence": 0.9,
  "reasoning": "両方のコードは同じ機能を実装しているが、異なる実装方法を使用している。変数名や処理フローが異なるが、最終的な結果は同じ。",
  "details": {
    "functional_similarity": 0.9,
    "intent_similarity": 0.8,
    "implementation_similarity": 0.7
  }
}

注意：
- similarity: 0.0-1.0の範囲で意味的類似度を評価
- confidence: 0.0-1.0の範囲で分析の信頼度を評価
- reasoning: 判定理由を日本語で説明
```

## 4. Response Parsing Logic

The response parsing happens in `_parse_llm_response` (lines 253-278):

1. Attempts to extract JSON using regex: `r'\{.*\}'`
2. Parses the JSON string
3. Validates and clamps values to 0.0-1.0 range
4. Falls back to keyword-based parsing if JSON parsing fails

## 5. Potential Issues

### 5.1 Code Formatting in Prompt
The most likely cause of "unexpected indent" errors is that the code being analyzed contains:
- Mixed indentation (tabs vs spaces)
- Incorrect indentation levels
- Code that's already malformed

### 5.2 LLM Response Issues
- The LLM might return malformed JSON
- The response might not follow the expected format
- Network timeouts or connection issues

### 5.3 JSON Extraction
The regex `r'\{.*\}'` is greedy and might capture too much if there are multiple JSON-like structures in the response.

## 6. Recommendations

1. **Validate Input Code**: Check if the code fragments are syntactically valid before sending to LLM
2. **Escape Code Properly**: Ensure proper escaping of code in the prompt
3. **Improve JSON Extraction**: Use a more robust method to extract JSON from LLM response
4. **Add Better Error Handling**: Provide more specific error messages about what went wrong
5. **Log Raw Responses**: Log the raw LLM response when parsing fails for debugging

## 7. Error Flow

1. `SemanticAwareDuplicateDetector.detect_duplicates()` calls `_analyze_semantic_duplicates()`
2. `_analyze_semantic_duplicates()` calls `analyze_semantic_similarity()` on the facade
3. The facade calls `semantic_analyzer.analyze_similarity()`
4. This calls `_llm_semantic_analysis()` which uses the LLM provider
5. The LLM provider makes an HTTP request and can raise `LLMResponseError`
6. The error is caught and falls back to structural analysis

## 8. Likely Root Cause

The "unexpected indent" error suggests that the code being analyzed has indentation issues. When this malformed code is included in the prompt, it might cause the LLM to produce unexpected output or the JSON parsing to fail.

To fix this:
1. Pre-validate code syntax before analysis
2. Handle syntax errors gracefully
3. Consider normalizing indentation before sending to LLM