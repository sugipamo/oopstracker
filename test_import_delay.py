#!/usr/bin/env python3
"""Test to identify where the 15-second delay comes from."""

import time
import sys

def time_import(module_name, import_statement):
    """Time how long an import takes."""
    print(f"\nTiming import: {import_statement}")
    start = time.time()
    try:
        exec(import_statement)
        elapsed = time.time() - start
        print(f"  ✓ Success: {elapsed:.3f} seconds")
        return elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ✗ Failed: {e} ({elapsed:.3f} seconds)")
        return elapsed

def main():
    """Run import timing tests."""
    print("Testing import delays for oopstracker...")
    print("=" * 60)
    
    total_time = 0
    
    # Test individual imports
    imports_to_test = [
        ("models", "from oopstracker.models import CodeRecord"),
        ("ast_simhash_detector", "from oopstracker.ast_simhash_detector import ASTSimHashDetector"),
        ("semantic_detector", "from oopstracker.semantic_detector import SemanticAwareDuplicateDetector"),
        ("cli", "from oopstracker import cli"),
        ("ai_analysis_coordinator", "from oopstracker.ai_analysis_coordinator import AIAnalysisCoordinator"),
        ("function_taxonomy_expert", "from oopstracker.function_taxonomy_expert import FunctionTaxonomyExpert"),
    ]
    
    for name, import_stmt in imports_to_test:
        elapsed = time_import(name, import_stmt)
        total_time += elapsed
        if elapsed > 1.0:
            print(f"  ⚠️  SLOW IMPORT DETECTED!")
    
    print(f"\nTotal import time: {total_time:.3f} seconds")
    
    # Now test the actual CLI command
    print("\n" + "=" * 60)
    print("Testing full CLI startup...")
    start = time.time()
    try:
        from oopstracker.cli import main
        elapsed = time.time() - start
        print(f"CLI import time: {elapsed:.3f} seconds")
    except Exception as e:
        elapsed = time.time() - start
        print(f"CLI import failed: {e} ({elapsed:.3f} seconds)")

if __name__ == "__main__":
    main()