#!/usr/bin/env python3
"""
Realistic test with 500 functions and proper mock LLM.
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oopstracker.smart_group_splitter import SmartGroupSplitter
from oopstracker.function_group_clustering import FunctionGroup


def create_realistic_test_functions():
    """Create 500 realistic functions with various patterns."""
    functions = []
    
    # User management functions (100)
    for i in range(100):
        operation = ['create', 'update', 'delete', 'get', 'list'][i % 5]
        entity = ['user', 'profile', 'account', 'session', 'role'][i % 5]
        func_name = f"{operation}_{entity}_{i}"
        functions.append({
            'name': func_name,
            'code': f'def {func_name}(data): pass',
            'file_path': f'users/{operation}_{entity}.py',
            'category': 'user_management'
        })
    
    # API endpoints (100)
    for i in range(100):
        method = ['get', 'post', 'put', 'delete', 'patch'][i % 5]
        resource = ['order', 'product', 'customer', 'invoice', 'payment'][i % 5]
        func_name = f"handle_{method}_{resource}_{i}"
        functions.append({
            'name': func_name,
            'code': f'def {func_name}(request): pass',
            'file_path': f'api/{resource}_endpoints.py',
            'category': 'api'
        })
    
    # Data validation functions (100)
    for i in range(100):
        action = ['validate', 'check', 'verify', 'ensure', 'assert'][i % 5]
        data_type = ['email', 'phone', 'date', 'amount', 'address'][i % 5]
        func_name = f"{action}_{data_type}_{i}"
        functions.append({
            'name': func_name,
            'code': f'def {func_name}(value): pass',
            'file_path': f'validators/{data_type}_validator.py',
            'category': 'validation'
        })
    
    # Database operations (100)
    for i in range(100):
        operation = ['query', 'insert', 'update', 'delete', 'migrate'][i % 5]
        table = ['orders', 'products', 'users', 'logs', 'settings'][i % 5]
        func_name = f"{operation}_{table}_{i}"
        functions.append({
            'name': func_name,
            'code': f'def {func_name}(conn, data): pass',
            'file_path': f'database/{table}_ops.py',
            'category': 'database'
        })
    
    # Utility functions (100)
    for i in range(100):
        util_type = ['format', 'parse', 'convert', 'transform', 'process'][i % 5]
        data = ['string', 'number', 'date', 'json', 'xml'][i % 5]
        func_name = f"{util_type}_{data}_{i}"
        functions.append({
            'name': func_name,
            'code': f'def {func_name}(input_data): pass',
            'file_path': f'utils/{data}_utils.py',
            'category': 'utility'
        })
    
    return functions


class SmartMockLLM:
    """Mock LLM that returns realistic splitting patterns."""
    
    def __init__(self):
        self.call_count = 0
        self.patterns = [
            # Pattern 1: Split by operation type (CRUD)
            {
                'pattern': r'def\s+(create|insert|add)_',
                'reason': 'Group all creation/insertion operations together'
            },
            # Pattern 2: Split by validation vs processing
            {
                'pattern': r'def\s+(validate|check|verify|ensure|assert)_',
                'reason': 'Separate validation logic from business logic'
            },
            # Pattern 3: Split by async vs sync
            {
                'pattern': r'def\s+handle_(get|post)_',
                'reason': 'Group HTTP GET/POST handlers separately from other operations'
            },
            # Pattern 4: Split by data access pattern
            {
                'pattern': r'def\s+(query|select|fetch|retrieve)_',
                'reason': 'Group read operations separately from write operations'
            },
            # Pattern 5: Split by resource type
            {
                'pattern': r'def\s+\w+_(user|profile|account|session)_',
                'reason': 'Group user-related functions together'
            },
            # Pattern 6: Split by numeric suffix (even/odd)
            {
                'pattern': r'def\s+\w+_[0-9]*[02468]$',
                'reason': 'Split functions with even-numbered suffixes'
            },
            # Pattern 7: Split by utility type
            {
                'pattern': r'def\s+(format|parse)_',
                'reason': 'Separate formatting/parsing utilities from other processing'
            },
            # Pattern 8: Split by entity type
            {
                'pattern': r'def\s+\w+_(order|product|customer)_',
                'reason': 'Group e-commerce related functions'
            }
        ]
    
    def get_next_pattern(self):
        """Get the next pattern in sequence."""
        pattern_info = self.patterns[self.call_count % len(self.patterns)]
        self.call_count += 1
        return pattern_info['pattern'], pattern_info['reason']


# Global mock instance
mock_llm = SmartMockLLM()


async def mock_analyze_intent(prompt):
    """Mock analyze_intent that returns realistic patterns."""
    await asyncio.sleep(0.1)  # Simulate processing time
    
    pattern, reason = mock_llm.get_next_pattern()
    
    # Format response as expected by the parser
    result_text = f"PATTERN: {pattern}\nREASONING: {reason}"
    
    from oopstracker.ai_analysis_coordinator import AnalysisResponse
    return AnalysisResponse(
        success=True,
        result={'purpose': result_text},
        confidence=0.9,
        reasoning="Mock pattern generation",
        metadata={},
        processing_time=0.1
    )


async def test_500_functions():
    """Test with 500 functions using realistic patterns."""
    print("🔬 Testing 500 Functions with Realistic Mock LLM")
    print("=" * 60)
    print(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
    
    # Create test data
    print("\n📁 Creating realistic test data...")
    functions = create_realistic_test_functions()
    print(f"   ✅ Created {len(functions)} functions in 5 categories")
    
    # Create initial group
    initial_group = FunctionGroup(
        group_id="all_functions",
        functions=functions,
        label="All Functions",
        confidence=0.8,
        metadata={}
    )
    
    print(f"\n📊 Initial state:")
    print(f"   Total functions: {len(functions)}")
    print(f"   Initial groups: 1")
    print(f"   Functions per group: {len(initial_group.functions)}")
    
    # Patch the mock LLM
    import oopstracker.ai_analysis_coordinator
    original_analyze = None
    if hasattr(oopstracker.ai_analysis_coordinator, 'MockAICoordinator'):
        original_analyze = oopstracker.ai_analysis_coordinator.MockAICoordinator.analyze_intent
        oopstracker.ai_analysis_coordinator.MockAICoordinator.analyze_intent = mock_analyze_intent
    
    # Apply smart splitting
    print("\n🤖 Applying LLM-based splitting (threshold: >100)...")
    start_time = time.time()
    
    splitter = SmartGroupSplitter(enable_ai=True, use_mock_ai=True)
    
    # Track splitting progress
    iteration = 1
    current_groups = [initial_group]
    
    while any(len(g.functions) > 100 for g in current_groups) and iteration <= 10:
        print(f"\n   Iteration {iteration}:")
        groups_to_split = [g for g in current_groups if len(g.functions) > 100]
        print(f"   - Groups needing split: {len(groups_to_split)}")
        
        # Apply one round of splitting
        new_groups = await splitter.split_large_groups_with_llm(current_groups, max_depth=1)
        
        # Show what happened
        print(f"   - Groups after split: {len(new_groups)}")
        for i, g in enumerate(new_groups):
            if len(g.functions) > 20:  # Only show larger groups
                print(f"     Group {i+1}: {len(g.functions)} functions - {g.label}")
        
        current_groups = new_groups
        iteration += 1
    
    final_groups = current_groups
    splitting_time = time.time() - start_time
    
    print(f"\n✅ Splitting completed in {splitting_time:.1f}s")
    
    # Analysis
    print("\n📈 Final Results:")
    
    # Group size distribution
    sizes = [len(g.functions) for g in final_groups]
    print(f"\n   Group statistics:")
    print(f"   - Total groups: {len(final_groups)}")
    print(f"   - Smallest group: {min(sizes)} functions")
    print(f"   - Largest group: {max(sizes)} functions")
    print(f"   - Average size: {sum(sizes) / len(sizes):.1f} functions")
    
    # Size categories
    small = len([s for s in sizes if s <= 50])
    medium = len([s for s in sizes if 50 < s <= 100])
    large = len([s for s in sizes if s > 100])
    
    print(f"\n   Size distribution:")
    print(f"   - Small (≤50): {small} groups")
    print(f"   - Medium (51-100): {medium} groups")
    print(f"   - Large (>100): {large} groups")
    
    # Show final groups
    print(f"\n   Final groups:")
    for i, group in enumerate(sorted(final_groups, key=lambda g: len(g.functions), reverse=True)):
        if i < 10:  # Show top 10
            pattern = group.metadata.get('split_rule', 'initial')
            print(f"   {i+1}. {group.label}: {len(group.functions)} functions")
            if pattern != 'initial':
                print(f"      Pattern: {pattern}")
    
    # Verify all functions are accounted for
    total_functions_in_groups = sum(len(g.functions) for g in final_groups)
    print(f"\n   Verification:")
    print(f"   - Original functions: {len(functions)}")
    print(f"   - Functions in final groups: {total_functions_in_groups}")
    print(f"   - {'✅ All functions accounted for' if total_functions_in_groups == len(functions) else '❌ Function count mismatch!'}")
    
    # Restore original mock
    if original_analyze:
        oopstracker.ai_analysis_coordinator.MockAICoordinator.analyze_intent = original_analyze
    
    print(f"\n⏰ End time: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    return final_groups


if __name__ == "__main__":
    asyncio.run(test_500_functions())