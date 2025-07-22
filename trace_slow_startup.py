#!/usr/bin/env python3
"""Trace where the 15-second delay happens during oopstracker check."""

import time
import sys
import functools
import importlib.util

# Track timing
start_time = time.time()
import_times = {}

def log_time(msg):
    """Log with timestamp."""
    elapsed = time.time() - start_time
    print(f"[{elapsed:6.3f}s] {msg}", file=sys.stderr)

# Hook into import system to track slow imports
original_import = __builtins__.__import__

def timed_import(name, *args, **kwargs):
    """Track import times."""
    import_start = time.time()
    try:
        module = original_import(name, *args, **kwargs)
        import_time = time.time() - import_start
        if import_time > 0.1:  # Only log slow imports
            log_time(f"SLOW IMPORT: {name} took {import_time:.3f}s")
        import_times[name] = import_time
        return module
    except Exception as e:
        import_time = time.time() - import_start
        log_time(f"FAILED IMPORT: {name} ({import_time:.3f}s) - {e}")
        raise

# Install the hook
__builtins__.__import__ = timed_import

log_time("Import hook installed, starting trace...")

# Now try to run the check command
try:
    log_time("Setting up environment...")
    import os
    import subprocess
    
    # Get the command that would be run
    cmd = [sys.executable, "-m", "oopstracker", "check", "src/oopstracker", "--quiet"]
    
    log_time(f"Running command: {' '.join(cmd)}")
    
    # Run with timeout
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
        cwd="/home/coding/code-smith/code-generation/intent/ast-analysis/oopstracker"
    )
    
    log_time(f"Command completed with return code: {result.returncode}")
    
    if result.stdout:
        print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
        
except subprocess.TimeoutExpired:
    log_time("Command timed out after 30 seconds!")
except Exception as e:
    log_time(f"Error: {e}")

# Show slow imports
log_time("Top slow imports:")
sorted_imports = sorted(import_times.items(), key=lambda x: x[1], reverse=True)
for name, duration in sorted_imports[:10]:
    if duration > 0.05:
        log_time(f"  {name}: {duration:.3f}s")