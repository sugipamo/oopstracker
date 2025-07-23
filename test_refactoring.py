"""Test script to verify the refactored semantic detector."""

import asyncio
import sys
sys.path.insert(0, '/home/coding/code-smith/evocraft/packages/oopstracker/src')

from oopstracker.models import CodeRecord
from oopstracker.semantic_detector import SemanticAwareDuplicateDetector


async def test_refactored_detector():
    """Test the refactored semantic detector."""
    print("Testing refactored semantic detector...")
    
    # Create test code records
    code_records = [
        CodeRecord(
            code_hash="hash1",
            code_content="""def calculate_sum(a, b):
    return a + b""",
            function_name="calculate_sum",
            file_path="test1.py"
        ),
        CodeRecord(
            code_hash="hash2",
            code_content="""def add_numbers(x, y):
    return x + y""",
            function_name="add_numbers",
            file_path="test2.py"
        ),
        CodeRecord(
            code_hash="hash3",
            code_content="""def multiply(a, b):
    return a * b""",
            function_name="multiply",
            file_path="test3.py"
        )
    ]
    
    # Initialize detector
    detector = SemanticAwareDuplicateDetector(
        intent_unified_available=False,  # Disable for testing
        enable_intent_tree=False
    )
    
    try:
        # Initialize
        await detector.initialize()
        print("✅ Initialization successful")
        
        # Run duplicate detection
        results = await detector.detect_duplicates(
            code_records,
            enable_semantic=False  # Structural only for testing
        )
        
        print("\n📊 Detection Results:")
        print(f"- Structural duplicates found: {results['structural_duplicates']['total_found']}")
        print(f"- High confidence: {len(results['structural_duplicates']['high_confidence'])}")
        print(f"- Medium confidence: {len(results['structural_duplicates']['medium_confidence'])}")
        
        # Test quick semantic check
        similarity = await detector.quick_semantic_check(
            code_records[0].code_content,
            code_records[1].code_content
        )
        print(f"\n🔍 Quick semantic check similarity: {similarity}")
        
        # Cleanup
        await detector.cleanup()
        print("\n✅ Cleanup successful")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_refactored_detector())