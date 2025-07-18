#!/usr/bin/env python3
"""Test semantic analyzer initialization."""

import asyncio
import logging
import sys

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Import necessary modules
from intent_unified.config.settings import UnifiedConfig
from intent_unified.core.semantic_analyzer import SemanticDuplicateAnalyzer, CodeFragment

async def test_semantic_analyzer():
    """Test semantic analyzer initialization."""
    
    # Create config
    config = UnifiedConfig()
    
    # Create analyzer
    analyzer = SemanticDuplicateAnalyzer(config)
    
    # Initialize
    print("Initializing semantic analyzer...")
    await analyzer.initialize()
    
    # Check if LLM provider is initialized
    print(f"LLM provider initialized: {analyzer._llm_provider is not None}")
    
    # Test analysis
    if analyzer._llm_provider:
        print("\nTesting semantic analysis...")
        
        code1 = CodeFragment("""
def add(a, b):
    return a + b
""")
        
        code2 = CodeFragment("""
def sum_two(x, y):
    return x + y
""")
        
        result = await analyzer.analyze_similarity(code1, code2)
        print(f"Analysis result: {result}")
    else:
        print("LLM provider not initialized, cannot test analysis")

if __name__ == "__main__":
    asyncio.run(test_semantic_analyzer())