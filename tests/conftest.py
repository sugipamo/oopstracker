"""pytest configuration for oopstracker tests."""

import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_directory():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_python_files(temp_directory):
    """Create sample Python files for testing."""
    files = {}
    
    # Simple function file
    simple_file = temp_directory / "simple.py"
    simple_file.write_text('''
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
''')
    files["simple"] = simple_file
    
    # Class-based file
    class_file = temp_directory / "classes.py"
    class_file.write_text('''
class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, value):
        self.result += value
        return self.result
    
    def reset(self):
        self.result = 0
''')
    files["class"] = class_file
    
    # Complex file with multiple features
    complex_file = temp_directory / "complex.py"
    complex_file.write_text('''
import os
import sys
from typing import List, Dict

@dataclass
class DataPoint:
    x: float
    y: float
    
    def distance(self, other):
        return ((self.x - other.x)**2 + (self.y - other.y)**2)**0.5

def process_data(data: List[DataPoint]) -> Dict[str, float]:
    """Process data points and return statistics."""
    if not data:
        return {}
    
    total_x = sum(p.x for p in data)
    total_y = sum(p.y for p in data)
    
    return {
        "mean_x": total_x / len(data),
        "mean_y": total_y / len(data),
        "count": len(data)
    }
''')
    files["complex"] = complex_file
    
    return files


@pytest.fixture
def similar_code_pairs():
    """Provide pairs of similar code for testing similarity detection."""
    return [
        # Identical except for variable names
        ('''
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total
''', '''
def calculate_sum(values):
    sum_val = 0
    for val in values:
        sum_val += val
    return sum_val
'''),
        
        # Similar structure, different implementation
        ('''
class Stack:
    def __init__(self):
        self.items = []
    
    def push(self, item):
        self.items.append(item)
    
    def pop(self):
        return self.items.pop()
''', '''
class Stack:
    def __init__(self):
        self.data = []
    
    def push(self, element):
        self.data.append(element)
    
    def pop(self):
        if self.data:
            return self.data.pop()
        return None
'''),
    ]


@pytest.fixture
def different_code_pairs():
    """Provide pairs of different code for testing dissimilarity detection."""
    return [
        # Completely different functionality
        ('''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
''', '''
import requests

def fetch_data(url):
    response = requests.get(url)
    return response.json()
'''),
        
        # Different patterns and structure
        ('''
class Observer:
    def update(self, subject):
        pass

class Subject:
    def __init__(self):
        self.observers = []
    
    def attach(self, observer):
        self.observers.append(observer)
''', '''
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
'''),
    ]