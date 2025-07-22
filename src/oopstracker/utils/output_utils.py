"""
Output utilities for OOPStracker.
"""
import contextlib
import sys
from io import StringIO


@contextlib.contextmanager
def suppress_unwanted_output():
    """Context manager to suppress unwanted stdout messages from external libraries."""
    
    class FilteredStdout:
        def __init__(self, original_stdout):
            self.original_stdout = original_stdout
            self.buffer = StringIO()
            
        def write(self, text):
            # Filter out unwanted messages
            unwanted_patterns = [
                "Session",
                "is not active",
                "status: completed",
                "warning: `VIRTUAL_ENV=",
                "does not match the project environment path"
            ]
            
            if not any(pattern in text for pattern in unwanted_patterns):
                self.original_stdout.write(text)
            else:
                # Suppress the unwanted message
                pass
                
        def flush(self):
            self.original_stdout.flush()
            
        def __getattr__(self, name):
            # Forward all other attributes to the original stdout
            return getattr(self.original_stdout, name)
    
    # Replace stdout temporarily
    original_stdout = sys.stdout
    sys.stdout = FilteredStdout(original_stdout)
    
    try:
        yield
    finally:
        # Restore original stdout
        sys.stdout = original_stdout