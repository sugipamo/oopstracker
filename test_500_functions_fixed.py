#!/usr/bin/env python3
"""
Fixed test with 500 functions and better mock pattern generation.
"""

import asyncio
import sys
import time
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oopstracker.smart_group_splitter import SmartGroupSplitter
from oopstracker.function_group_clustering import FunctionGroup
from oopstracker.ai_analysis_coordinator import get_ai_coordinator


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


async def test_with_better_patterns():
    """Test splitting logic with fixed patterns."""
    print("🔬 Testing 500 Functions with Fixed Mock Patterns")
    print("=" * 60)
    print(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
    
    # Create test data
    print("\n📁 Creating realistic test data...")
    functions = create_realistic_test_functions()
    print(f"   ✅ Created {len(functions)} functions in 5 categories")
    
    # Show category distribution
    categories = {}
    for func in functions:
        cat = func['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\n   Category distribution:")
    for cat, count in categories.items():
        print(f"   - {cat}: {count} functions")
    
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
    
    # Prepare patterns that will actually work
    test_patterns = [
        # Pattern to split create/update/delete operations
        r'def\s+(create|update|delete)_',
        # Pattern to split validation functions
        r'def\s+(validate|check|verify)_',
        # Pattern to split by even numbers
        r'def\s+\w+_\d*[02468]\s*\(',
        # Pattern to split user-related functions
        r'def\s+\w+_(user|profile|account)_',
        # Pattern to split by numeric ranges
        r'def\s+\w+_[0-4]\d\s*\('
    ]
    
    # Test each pattern manually to show it works
    print("\n🧪 Testing patterns individually:")
    for i, pattern in enumerate(test_patterns[:3]):
        matches = 0
        for func in functions:
            if re.search(pattern, func['code']):
                matches += 1
        print(f"   Pattern {i+1}: '{pattern[:30]}...' matches {matches} functions")
    
    # Apply smart splitting
    print("\n🤖 Applying LLM-based splitting...")
    start_time = time.time()
    
    splitter = SmartGroupSplitter(enable_ai=True, use_mock_ai=True)
    
    # Manually test splitting with known good pattern
    print("\n   Testing manual split with even/odd pattern:")
    even_pattern = r'def\s+\w+_\d*[02468]\s*\('
    is_valid, matched, unmatched = splitter.validate_split(initial_group, even_pattern)
    if is_valid:
        print(f"   ✅ Valid split: {len(matched)} matched, {len(unmatched)} unmatched")
    else:
        print(f"   ❌ Invalid split")
    
    # Now try the automatic splitting
    print("\n   Running automatic LLM-based splitting:")
    
    try:
        # Try splitting with reduced recursion depth
        final_groups = await splitter.split_large_groups_with_llm([initial_group], max_depth=2)
        
        splitting_time = time.time() - start_time
        print(f"\n✅ Splitting completed in {splitting_time:.1f}s")
        
        # Analysis
        print("\n📈 Results:")
        sizes = [len(g.functions) for g in final_groups]
        print(f"   - Groups created: {len(final_groups)}")
        print(f"   - Smallest group: {min(sizes)} functions")
        print(f"   - Largest group: {max(sizes)} functions")
        print(f"   - Average size: {sum(sizes) / len(sizes):.1f} functions")
        
        # Show groups
        print("\n   Final groups:")
        for i, group in enumerate(final_groups):
            print(f"   {i+1}. {group.label}: {len(group.functions)} functions")
            if 'split_rule' in group.metadata:
                print(f"      Rule: {group.metadata['split_rule']}")
        
    except Exception as e:
        print(f"\n❌ Error during splitting: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n⏰ End time: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_with_better_patterns())