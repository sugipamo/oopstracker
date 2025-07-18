#!/usr/bin/env python3
"""Test OOPStracker behavior when no LLM is available."""

import os
import sys
import subprocess

# Temporarily block LLM endpoints by setting invalid URL
env = os.environ.copy()
env["OOPSTRACKER_LLM_URL"] = "http://invalid-host:9999/api/chat"

# Run oopstracker with invalid LLM
print("Running OOPStracker with no LLM available...\n")
result = subprocess.run(
    ["uv", "run", "oopstracker", "check", "--limit", "1"],
    env=env,
    capture_output=True,
    text=True,
    cwd="/home/coding/code-smith/code-generation/intent/ast-analysis/oopstracker"
)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")