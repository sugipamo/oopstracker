#!/usr/bin/env python3
"""
Test with a properly working mock LLM that generates valid patterns.
"""

import asyncio
import sys
import re
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oopstracker.smart_group_splitter import SmartGroupSplitter
from oopstracker.function_group_clustering import FunctionGroup
from oopstracker.ai_analysis_coordinator import AnalysisResponse


class WorkingMockLLM:
    """Mock LLM that generates patterns that actually work with test data."""
    
    def __init__(self):
        self.call_count = 0
        self.patterns = [
            # Pattern 1: Split by operation type (create vs others)
            {
                'pattern': r'def\s+(create)_',
                'reasoning': 'Group creation operations separately from other operations'
            },
            # Pattern 2: Split by validation functions
            {
                'pattern': r'def\s+(validate|check|verify)_',
                'reasoning': 'Group validation functions separately from business logic'
            },
            # Pattern 3: Split by HTTP method handlers
            {
                'pattern': r'def\s+handle_(get|post)_',
                'reasoning': 'Group GET/POST handlers separately from other HTTP methods'
            },
            # Pattern 4: Split by even numbers
            {
                'pattern': r'def\s+\w+_\d*[02468]\s*\(',
                'reasoning': 'Split functions with even-numbered suffixes for load balancing'
            },
            # Pattern 5: Split by user-related functions
            {
                'pattern': r'def\s+\w+_(user|profile|account)_',
                'reasoning': 'Group user-related functions together'
            }
        ]
    
    async def analyze_intent(self, code: str, **kwargs) -> AnalysisResponse:
        """Mock analyze_intent that returns working patterns."""
        await asyncio.sleep(0.01)
        
        # Check if this is a pattern generation request
        if "PATTERN:" in code and "REASONING:" in code:
            # Get the next pattern that should work
            pattern_info = self.patterns[self.call_count % len(self.patterns)]
            self.call_count += 1
            
            response_text = f"PATTERN: {pattern_info['pattern']}\nREASONING: {pattern_info['reasoning']}"
            
            return AnalysisResponse(
                success=True,
                result={"purpose": response_text},
                confidence=0.9,
                reasoning="Working mock pattern generation",
                metadata={"analysis_method": "working_mock"},
                processing_time=0.01
            )
        
        # Regular intent analysis
        return AnalysisResponse(
            success=True,
            result={"purpose": "Mock intent analysis", "functionality": "Test functionality"},
            confidence=0.7,
            reasoning="Mock analysis",
            metadata={},
            processing_time=0.01
        )


async def test_with_working_mock():
    """Test splitting with a working mock LLM."""
    print("🔧 Testing with Working Mock LLM")
    print("=" * 50)
    print(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
    
    # Create realistic test functions (500 total)
    functions = []
    
    # Create functions (100 each type = 500 total)
    for i in range(100):
        functions.extend([
            {'name': f'create_user_{i}', 'code': f'def create_user_{i}(data): pass'},
            {'name': f'update_user_{i}', 'code': f'def update_user_{i}(data): pass'},
            {'name': f'validate_email_{i}', 'code': f'def validate_email_{i}(value): pass'},
            {'name': f'handle_get_order_{i}', 'code': f'def handle_get_order_{i}(request): pass'},
            {'name': f'query_database_{i}', 'code': f'def query_database_{i}(sql): pass'}
        ])
    
    print(f"\n📊 Test data: {len(functions)} functions")
    
    # Count by pattern
    create_count = len([f for f in functions if 'create_' in f['name']])
    validate_count = len([f for f in functions if 'validate_' in f['name']])
    handle_count = len([f for f in functions if 'handle_' in f['name']])
    even_count = len([f for f in functions if re.search(r'_\d*[02468]\s*\(', f['code'])])
    
    print(f"   - create_* functions: {create_count}")
    print(f"   - validate_* functions: {validate_count}")  
    print(f"   - handle_* functions: {handle_count}")
    print(f"   - even-numbered functions: {even_count}")
    
    # Create initial group
    initial_group = FunctionGroup(
        group_id="large_group",
        functions=functions,
        label="Large Test Group",
        confidence=0.8,
        metadata={}
    )
    
    print(f"\n📈 Initial group: {len(functions)} functions (exceeds threshold of 100)")
    
    # Create splitter and patch with working mock
    splitter = SmartGroupSplitter(enable_ai=True, use_mock_ai=True)
    
    # Replace the AI coordinator with our working mock
    working_mock = WorkingMockLLM()
    
    # Patch the generate_split_regex_with_llm method
    original_method = splitter.generate_split_regex_with_llm
    
    async def patched_generate_split_regex_with_llm(sample_functions):
        # Create a mock prompt
        mock_prompt = "PATTERN:\nREASONING:"
        response = await working_mock.analyze_intent(mock_prompt)
        
        result_text = response.result['purpose']
        pattern_match = re.search(r'PATTERN:\s*(.+)', result_text, re.IGNORECASE)
        reasoning_match = re.search(r'REASONING:\s*(.+)', result_text, re.IGNORECASE | re.DOTALL)
        
        if not pattern_match:
            raise RuntimeError("No pattern found in mock response")
        
        pattern = pattern_match.group(1).strip()
        reasoning = reasoning_match.group(1).strip() if reasoning_match else "Mock reasoning"
        
        return pattern, reasoning
    
    # Apply the patch
    splitter.generate_split_regex_with_llm = patched_generate_split_regex_with_llm
    
    # Test splitting
    print("\n🤖 Applying LLM-based splitting...")
    start_time = time.time()
    
    try:
        final_groups = await splitter.split_large_groups_with_llm([initial_group], max_depth=3)
        elapsed_time = time.time() - start_time
        
        print(f"✅ Splitting completed in {elapsed_time:.2f}s")
        
        # Analyze results
        print(f"\n📊 Results:")
        print(f"   - Original groups: 1")
        print(f"   - Final groups: {len(final_groups)}")
        
        sizes = [len(g.functions) for g in final_groups]
        print(f"   - Smallest group: {min(sizes)} functions")
        print(f"   - Largest group: {max(sizes)} functions")
        print(f"   - Average size: {sum(sizes) / len(sizes):.1f} functions")
        
        # Check if we successfully split large groups
        large_groups = [g for g in final_groups if len(g.functions) > 100]
        print(f"   - Groups still >100: {len(large_groups)}")
        
        # Show final groups
        print(f"\n📋 Final groups:")
        for i, group in enumerate(sorted(final_groups, key=lambda g: len(g.functions), reverse=True)[:10]):
            pattern = group.metadata.get('split_rule', 'N/A')
            print(f"   {i+1}. {group.label}: {len(group.functions)} functions")
            if pattern != 'N/A':
                print(f"      Pattern: {pattern}")
        
        # Verify function accounting
        total_functions_in_groups = sum(len(g.functions) for g in final_groups)
        print(f"\n✅ Function accounting:")
        print(f"   - Original: {len(functions)}")
        print(f"   - Final: {total_functions_in_groups}")
        print(f"   - Match: {'✅' if total_functions_in_groups == len(functions) else '❌'}")
        
        if len(large_groups) == 0:
            print(f"\n🎯 SUCCESS: All groups split to ≤100 functions!")
        else:
            print(f"\n⚠️  Some groups still >100 (hit max depth)")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n⏰ End time: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_with_working_mock())