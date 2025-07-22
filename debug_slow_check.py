#!/usr/bin/env python3
"""Debug slow check command."""

import time
import sys
import asyncio

# Track time from start
start_time = time.time()

def timed_print(msg):
    """Print with timing info."""
    elapsed = time.time() - start_time
    print(f"[{elapsed:6.3f}s] {msg}")

timed_print("Starting debug...")

# Step 1: Import CLI components
timed_print("Importing argparse...")
import argparse

timed_print("Importing models...")
from oopstracker.models import CodeRecord

timed_print("Importing AST detector...")
from oopstracker.ast_simhash_detector import ASTSimHashDetector

timed_print("Importing semantic detector...")
try:
    from oopstracker.semantic_detector import SemanticAwareDuplicateDetector
except Exception as e:
    timed_print(f"Failed to import semantic detector: {e}")
    SemanticAwareDuplicateDetector = None

# Step 2: Initialize detector
timed_print("Creating AST detector...")
detector = ASTSimHashDetector()

# Step 3: Try semantic detector if available
if SemanticAwareDuplicateDetector:
    timed_print("Creating semantic detector...")
    semantic_detector = SemanticAwareDuplicateDetector(intent_unified_available=True, enable_intent_tree=True)
    
    async def init_semantic():
        timed_print("Initializing semantic detector...")
        await semantic_detector.initialize()
        timed_print("Semantic detector initialized")
    
    asyncio.run(init_semantic())

# Step 4: Import taxonomy expert (this might be slow)
timed_print("Importing function taxonomy expert...")
from oopstracker.function_taxonomy_expert import FunctionTaxonomyExpert

timed_print("Creating taxonomy expert...")
taxonomy_expert = FunctionTaxonomyExpert(enable_ai=True, use_mock_ai=False)

timed_print("Debug complete!")
print(f"\nTotal time: {time.time() - start_time:.3f}s")