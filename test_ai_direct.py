#!/usr/bin/env python3
"""Direct test of AI classification."""

import asyncio
import logging
from oopstracker.function_taxonomy_expert import FunctionTaxonomyExpert, AnalysisMethod

logging.basicConfig(level=logging.DEBUG)

async def main():
    print("Testing AI classification directly...")
    
    expert = FunctionTaxonomyExpert(enable_ai=True)
    
    test_code = """
def get_user_name(user_id):
    '''Get user name from database.'''
    return database.query(f"SELECT name FROM users WHERE id={user_id}")
"""
    
    # Test with only AI classification
    result = await expert.classify_function_purpose(
        test_code,
        "get_user_name",
        analysis_methods=[AnalysisMethod.AI_CLASSIFICATION]
    )
    
    print(f"\nResult:")
    print(f"  Category: {result.primary_category}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Methods: {result.analysis_methods}")
    print(f"  Reasoning: {result.reasoning}")

if __name__ == "__main__":
    asyncio.run(main())