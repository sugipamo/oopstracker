#!/usr/bin/env python3
"""Test AI clustering functionality."""

import asyncio
import logging
from oopstracker.function_group_clustering import FunctionGroupClusteringSystem, ClusteringStrategy

logging.basicConfig(level=logging.DEBUG)

async def main():
    print("Testing AI clustering...")
    
    # Test functions
    test_functions = [
        {
            'name': 'get_user_name',
            'file': 'test.py',
            'code': 'def get_user_name(user_id):\n    return db.query(user_id)',
            'line_number': 1
        },
        {
            'name': 'calculate_total',
            'file': 'test.py',
            'code': 'def calculate_total(items):\n    return sum(item.price for item in items)',
            'line_number': 10
        },
        {
            'name': 'validate_email',
            'file': 'test.py', 
            'code': 'def validate_email(email):\n    return "@" in email',
            'line_number': 20
        }
    ]
    
    # Create clustering system
    clustering_system = FunctionGroupClusteringSystem(enable_ai=True)
    
    # Get clusters
    clusters = await clustering_system.get_current_function_clusters(
        test_functions, 
        ClusteringStrategy.CATEGORY_BASED
    )
    
    print(f"\nFound {len(clusters)} clusters:")
    for cluster in clusters:
        print(f"\n{cluster.label}:")
        print(f"  Functions: {len(cluster.functions)}")
        print(f"  Confidence: {cluster.confidence}")
        for func in cluster.functions:
            print(f"    - {func['name']} (category: {func.get('category', 'unknown')})")

if __name__ == "__main__":
    asyncio.run(main())