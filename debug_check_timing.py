#!/usr/bin/env python3
"""Debug timing of check command."""

import time
import sys
import asyncio
import os

# Monkey-patch print to add timestamps
original_print = print
start_time = time.time()

def timed_print(*args, **kwargs):
    """Print with timing info."""
    elapsed = time.time() - start_time
    prefix = f"[{elapsed:6.3f}s]"
    if args:
        args = (prefix, *args)
    original_print(*args, **kwargs)

# Replace print globally
import builtins
builtins.print = timed_print

# Now run the actual check command
print("Starting check command...")

# Set up minimal args
class Args:
    command = "check"
    path = "src/oopstracker"
    db = "oopstracker.db"
    hamming_threshold = 10
    similarity_threshold = 0.7
    semantic_analysis = False  # Disable to speed up
    semantic_threshold = 0.7
    semantic_timeout = 30.0
    max_semantic_concurrent = 3
    log_level = "INFO"
    verbose = False
    quiet = True
    pattern = "*.py"
    force = False
    no_gitignore = False
    include_tests = False
    duplicates = False
    duplicates_threshold = 0.8
    classification_only = True  # Focus on classification
    disable_duplicate_detection = True
    enable_clustering = False

# Import after patching print
from oopstracker.cli import _main_impl

# Run the main implementation
async def run():
    # Inject our args
    import argparse
    old_parse_args = argparse.ArgumentParser.parse_args
    def mock_parse_args(self):
        return Args()
    argparse.ArgumentParser.parse_args = mock_parse_args
    
    print("Running main implementation...")
    try:
        await _main_impl()
    except SystemExit:
        pass  # Expected
    finally:
        # Restore
        argparse.ArgumentParser.parse_args = old_parse_args

print("Starting async run...")
asyncio.run(run())
print(f"Total time: {time.time() - start_time:.3f}s")