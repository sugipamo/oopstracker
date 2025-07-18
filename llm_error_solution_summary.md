# LLMResponseError Root Cause and Solution Summary

## Problem Summary

The `LLMResponseError` occurs when analyzing code with syntax errors (particularly indentation issues) because:

1. **Malformed code is sent directly to the LLM** without validation
2. **The LLM struggles to analyze syntactically incorrect code**
3. **JSON parsing fails** when the LLM produces unexpected output

## Root Cause

When code with syntax errors like:
```python
def hello():
    print("Hello")
        print("World")  # Unexpected indent
```

Is included in the semantic analysis prompt, it causes cascading failures:
1. The malformed code is embedded in the prompt
2. The LLM may produce unpredictable responses
3. The JSON extraction regex captures the wrong content
4. JSON parsing fails, leading to `LLMResponseError`

## Proposed Solution

### 1. Pre-Validation of Code Syntax
```python
def validate_code_syntax(code: str, language: str = "python") -> CodeValidationResult:
    """Validate code syntax before sending to LLM."""
    try:
        ast.parse(code)
        return CodeValidationResult(True)
    except SyntaxError as e:
        return CodeValidationResult(False, error_message)
```

### 2. Indentation Normalization
```python
def normalize_code_indentation(code: str) -> str:
    """Normalize code indentation to use spaces consistently."""
    lines = code.split('\n')
    normalized_lines = [line.expandtabs(4) for line in lines]
    return '\n'.join(normalized_lines)
```

### 3. Improved JSON Parsing
```python
# Use more specific regex pattern
json_pattern = r'\{[^{}]*"similarity"[^{}]*"confidence"[^{}]*"reasoning"[^{}]*\}'
# Take the last match (actual response, not example)
json_matches = list(re.finditer(json_pattern, response, re.DOTALL))
if json_matches:
    json_str = json_matches[-1].group(0)
```

### 4. Better Error Handling
- Return early with meaningful error when code has syntax errors
- Log problematic responses for debugging
- Provide detailed metadata about failures

## Implementation Steps

1. **Update `semantic_analyzer.py`**:
   - Add code validation functions
   - Modify `_llm_semantic_analysis` to validate code first
   - Replace `_parse_llm_response` with improved version

2. **Benefits**:
   - Prevents sending malformed code to LLM
   - Provides clear error messages for syntax issues
   - Handles mixed tabs/spaces automatically
   - More robust JSON extraction from LLM responses

3. **Minimal Changes Required**:
   - Add ~50 lines of validation code
   - Modify 2 existing methods
   - No API changes needed

## Testing Results

The proposed fixes successfully:
- ✅ Detect syntax errors before LLM analysis
- ✅ Normalize mixed indentation (tabs → spaces)
- ✅ Provide clear error messages
- ✅ Prevent LLMResponseError for malformed code

## Example Usage After Fix

```python
# Code with syntax error
code1 = "def hello():\n    print('Hello')\n        print('World')"  # Bad indent

# Instead of LLMResponseError, get:
# SemanticSimilarity(
#     similarity_score=0.0,
#     confidence=0.0,
#     method=AnalysisMethod.FAILED,
#     reasoning="Cannot analyze code with syntax errors: Code 1: Syntax error at line 3: unexpected indent",
#     metadata={"validation_errors": [...], "fallback_reason": "syntax_error"}
# )
```

## Files to Modify

1. `/home/coding/code-smith/code-generation/intent/intent-unified/src/intent_unified/core/semantic_analyzer.py`
   - Add validation functions
   - Update `_llm_semantic_analysis` method
   - Update `_parse_llm_response` method

The fix is backward compatible and doesn't change the public API.