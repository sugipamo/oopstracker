#!/usr/bin/env python3
"""Use Python's trace module to find where time is spent."""

import sys
import time
import trace
import os

# Create a Trace object, telling it what to ignore
tracer = trace.Trace(
    count=False,
    trace=False,
    timing=True
)

# Add the source directory to Python path
sys.path.insert(0, 'src')

print("Starting trace...")
start = time.time()

# Run the main function
try:
    tracer.run('from oopstracker.cli import main; main()')
except SystemExit:
    pass

elapsed = time.time() - start
print(f"\nTotal time: {elapsed:.3f}s")

# Get timing results
results = tracer.results()

# Show the slowest functions
print("\nSlowest functions:")
timing_data = []
for (filename, lineno, funcname), (count, total_time) in results.timings.items():
    if total_time > 0.1:  # Only show functions taking > 0.1s
        timing_data.append((total_time, filename, lineno, funcname))

timing_data.sort(reverse=True)
for total_time, filename, lineno, funcname in timing_data[:20]:
    # Simplify filename
    if '/site-packages/' in filename:
        filename = '...' + filename.split('/site-packages/')[-1]
    elif '/oopstracker/' in filename:
        filename = '...' + filename.split('/oopstracker/')[-1]
    print(f"{total_time:8.3f}s  {filename}:{lineno} ({funcname})")