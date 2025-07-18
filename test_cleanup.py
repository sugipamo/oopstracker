#!/usr/bin/env python3
"""Test cleanup functionality."""

import asyncio
import sys
sys.path.insert(0, '/home/coding/code-smith/code-generation/intent/ast-analysis/oopstracker/.venv/lib/python3.12/site-packages')

async def test_cleanup():
    from intent_unified import IntentUnifiedFacade
    
    print("Creating facade...")
    facade = IntentUnifiedFacade()
    
    print("Initializing...")
    await facade.__aenter__()
    
    print("Using semantic analyzer...")
    analyzer = facade.semantic_analyzer
    
    # Simple analysis
    from intent_unified.core.types import CodeFragment
    code1 = CodeFragment("def add(a, b): return a + b", "python")
    code2 = CodeFragment("def sum_two(x, y): return x + y", "python")
    
    result = await analyzer.analyze_similarity(code1, code2)
    print(f"Analysis result: {result.similarity_score}")
    
    print("Cleaning up...")
    await facade.__aexit__(None, None, None)
    
    print("Waiting for any pending tasks...")
    await asyncio.sleep(1)
    
    print("Done!")

if __name__ == "__main__":
    asyncio.run(test_cleanup())