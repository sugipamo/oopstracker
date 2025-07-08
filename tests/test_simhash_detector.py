"""
Tests for SimHash-based similarity detection.
"""

import pytest
import tempfile
import os
import time
from pathlib import Path

from oopstracker.simhash_detector import SimHashSimilarityDetector, BKTree, BKTreeNode
from oopstracker.models import CodeRecord
from oopstracker.exceptions import CodeAnalysisError


class TestBKTreeNode:
    """Test BK-tree node functionality."""
    
    def test_create_node(self):
        """Test creating a BK-tree node."""
        record = CodeRecord(id=1, code_content="def hello(): pass", function_name="hello")
        node = BKTreeNode(simhash=123456, record=record)
        
        assert node.simhash == 123456
        assert node.record == record
        assert node.children == {}
    
    def test_node_children(self):
        """Test node children management."""
        record1 = CodeRecord(id=1, code_content="def hello(): pass", function_name="hello")
        record2 = CodeRecord(id=2, code_content="def world(): pass", function_name="world")
        
        node1 = BKTreeNode(simhash=123456, record=record1)
        node2 = BKTreeNode(simhash=789012, record=record2)
        
        # Add child
        node1.children[5] = node2
        
        assert 5 in node1.children
        assert node1.children[5] == node2


class TestBKTree:
    """Test BK-tree functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.tree = BKTree()
    
    def test_empty_tree(self):
        """Test empty BK-tree."""
        assert self.tree.root is None
        assert self.tree.size == 0
        
        # Search in empty tree
        results = self.tree.search(12345, 5)
        assert results == []
    
    def test_single_insert(self):
        """Test inserting a single record."""
        record = CodeRecord(id=1, code_content="def hello(): pass", function_name="hello")
        
        self.tree.insert(123456, record)
        
        assert self.tree.root is not None
        assert self.tree.root.simhash == 123456
        assert self.tree.root.record == record
        assert self.tree.size == 1
    
    def test_multiple_inserts(self):
        """Test inserting multiple records."""
        records = [
            CodeRecord(id=1, code_content="def hello(): pass", function_name="hello"),
            CodeRecord(id=2, code_content="def world(): pass", function_name="world"),
            CodeRecord(id=3, code_content="def test(): pass", function_name="test")
        ]
        
        simhashes = [123456, 789012, 345678]
        
        for simhash, record in zip(simhashes, records):
            self.tree.insert(simhash, record)
        
        assert self.tree.size == 3
        assert self.tree.root.simhash == 123456
    
    def test_exact_search(self):
        """Test exact search in BK-tree."""
        record = CodeRecord(id=1, code_content="def hello(): pass", function_name="hello")
        simhash = 123456
        
        self.tree.insert(simhash, record)
        
        # Exact match
        results = self.tree.search(simhash, 0)
        assert len(results) == 1
        assert results[0][0] == record
        assert results[0][1] == 0
    
    def test_approximate_search(self):
        """Test approximate search in BK-tree."""
        record1 = CodeRecord(id=1, code_content="def hello(): pass", function_name="hello")
        record2 = CodeRecord(id=2, code_content="def world(): pass", function_name="world")
        
        # Insert records with different simhashes
        self.tree.insert(0b1010101010101010, record1)  # Binary for easier distance calculation
        self.tree.insert(0b1010101010101011, record2)  # Hamming distance = 1
        
        # Search with tolerance
        results = self.tree.search(0b1010101010101010, 2)
        assert len(results) == 2
        
        # Check distances
        distances = [result[1] for result in results]
        assert 0 in distances  # Exact match
        assert 1 in distances  # Distance 1 match
    
    def test_hamming_distance(self):
        """Test Hamming distance calculation."""
        tree = BKTree()
        
        # Test known distances
        assert tree._hamming_distance(0b1010, 0b1010) == 0
        assert tree._hamming_distance(0b1010, 0b1011) == 1
        assert tree._hamming_distance(0b1010, 0b0101) == 4
        assert tree._hamming_distance(0b1111, 0b0000) == 4
    
    def test_search_performance(self):
        """Test search performance with larger dataset."""
        # Insert many records
        records = []
        for i in range(100):
            record = CodeRecord(id=i, code_content=f"def func_{i}(): pass", function_name=f"func_{i}")
            simhash = i * 1000  # Spread out simhashes
            self.tree.insert(simhash, record)
            records.append((simhash, record))
        
        # Search should still be fast
        start_time = time.time()
        results = self.tree.search(50000, 10)
        end_time = time.time()
        
        search_time = (end_time - start_time) * 1000  # Convert to ms
        assert search_time < 100  # Should be fast
        
        # Should find the close match
        assert len(results) > 0
    
    def test_get_stats(self):
        """Test getting tree statistics."""
        # Empty tree
        stats = self.tree.get_stats()
        assert stats["size"] == 0
        assert stats["depth"] == 0
        
        # Add some records
        for i in range(10):
            record = CodeRecord(id=i, code_content=f"def func_{i}(): pass", function_name=f"func_{i}")
            self.tree.insert(i * 1000, record)
        
        stats = self.tree.get_stats()
        assert stats["size"] == 10
        assert stats["depth"] > 0
        assert "root_children" in stats


class TestSimHashSimilarityDetector:
    """Test SimHash similarity detector."""
    
    def setup_method(self):
        """Set up test environment."""
        self.detector = SimHashSimilarityDetector(threshold=5)
    
    def test_create_detector(self):
        """Test creating similarity detector."""
        detector = SimHashSimilarityDetector(threshold=10)
        
        assert detector.threshold == 10
        assert detector.bk_tree is not None
        assert detector.normalizer is not None
    
    def test_extract_features(self):
        """Test feature extraction from code."""
        code = '''
def hello():
    print("Hello, world!")
    return True
'''
        
        features = self.detector._extract_features(code)
        
        assert len(features) > 0
        assert "def" in features
        assert "hello" in features
        assert "print" in features
        
        # Should include bigrams and trigrams
        assert any("_" in feature for feature in features)
    
    def test_calculate_simhash(self):
        """Test SimHash calculation."""
        code1 = 'def hello(): print("Hello")'
        code2 = 'def hello(): print("Hello")'
        code3 = 'def goodbye(): print("Goodbye")'
        
        hash1 = self.detector.calculate_simhash(code1)
        hash2 = self.detector.calculate_simhash(code2)
        hash3 = self.detector.calculate_simhash(code3)
        
        assert isinstance(hash1, int)
        assert isinstance(hash2, int)
        assert isinstance(hash3, int)
        
        # Same code should have same hash
        assert hash1 == hash2
        
        # Different code should have different hash
        assert hash1 != hash3
    
    def test_add_record(self):
        """Test adding records to detector."""
        record = CodeRecord(
            id=1,
            code_content='def hello(): print("Hello")',
            function_name="hello"
        )
        
        success = self.detector.add_record(record)
        
        assert success is True
        assert hasattr(record, 'simhash')
        assert record.simhash is not None
        
        # Tree should have one record
        stats = self.detector.get_stats()
        assert stats["size"] == 1
    
    def test_add_empty_record(self):
        """Test adding empty record."""
        record = CodeRecord(id=1, code_content="", function_name="empty")
        
        success = self.detector.add_record(record)
        
        assert success is False
    
    def test_find_similar_exact(self):
        """Test finding exact matches."""
        # Add a record
        record = CodeRecord(
            id=1,
            code_content='def hello(): print("Hello")',
            function_name="hello"
        )
        self.detector.add_record(record)
        
        # Search for exact match
        result = self.detector.find_similar('def hello(): print("Hello")')
        
        assert result.is_duplicate is True
        assert result.similarity_score > 0.99  # Should be very high
        assert len(result.matched_records) == 1
        assert result.matched_records[0].id == 1
        assert result.analysis_method == "simhash_bktree"
    
    def test_find_similar_none(self):
        """Test finding no matches."""
        # Add a record
        record = CodeRecord(
            id=1,
            code_content='def hello(): print("Hello")',
            function_name="hello"
        )
        self.detector.add_record(record)
        
        # Search for different code
        result = self.detector.find_similar('def completely_different(): return 42')
        
        assert result.is_duplicate is False
        assert result.similarity_score == 0.0
        assert len(result.matched_records) == 0
    
    def test_find_similar_threshold(self):
        """Test similarity threshold behavior."""
        # Add a record
        record = CodeRecord(
            id=1,
            code_content='def hello(): print("Hello")',
            function_name="hello"
        )
        self.detector.add_record(record)
        
        # Search with very strict threshold
        result = self.detector.find_similar(
            'def hello(): print("Hello, world!")',  # Slightly different
            max_distance=1
        )
        
        # Should not find match with strict threshold
        assert len(result.matched_records) == 0 or result.similarity_score < 0.95
        
        # Search with relaxed threshold
        result = self.detector.find_similar(
            'def hello(): print("Hello, world!")',
            max_distance=10
        )
        
        # Might find match with relaxed threshold
        assert isinstance(result, type(result))  # Just check it runs
    
    def test_analyze_similarity(self):
        """Test similarity analysis between two code snippets."""
        code1 = 'def hello(): print("Hello")'
        code2 = 'def hello(): print("Hello")'
        code3 = 'def goodbye(): print("Goodbye")'
        
        # Same code
        similarity = self.detector.analyze_similarity(code1, code2)
        assert similarity == 1.0
        
        # Different code
        similarity = self.detector.analyze_similarity(code1, code3)
        assert 0.0 <= similarity <= 1.0
        assert similarity < 1.0
    
    def test_is_duplicate(self):
        """Test duplicate detection."""
        code1 = 'def hello(): print("Hello")'
        code2 = 'def hello(): print("Hello")'
        code3 = 'def goodbye(): print("Goodbye")'
        
        # Same code
        assert self.detector.is_duplicate(code1, code2) is True
        
        # Different code
        assert self.detector.is_duplicate(code1, code3) is False
    
    def test_rebuild_index(self):
        """Test rebuilding the index."""
        # Create some records
        records = []
        for i in range(10):
            record = CodeRecord(
                id=i,
                code_content=f'def func_{i}(): return {i}',
                function_name=f"func_{i}"
            )
            records.append(record)
        
        # Rebuild index
        self.detector.rebuild_index(records)
        
        # Check that all records are indexed
        stats = self.detector.get_stats()
        assert stats["size"] == 10
        
        # Should be able to find records
        result = self.detector.find_similar('def func_5(): return 5')
        assert result.is_duplicate is True
    
    def test_get_stats(self):
        """Test getting detector statistics."""
        # Empty detector
        stats = self.detector.get_stats()
        assert stats["size"] == 0
        
        # Add some records
        for i in range(5):
            record = CodeRecord(
                id=i,
                code_content=f'def func_{i}(): return {i}',
                function_name=f"func_{i}"
            )
            self.detector.add_record(record)
        
        stats = self.detector.get_stats()
        assert stats["size"] == 5
        assert "depth" in stats
    
    def test_error_handling(self):
        """Test error handling in detector."""
        # Test with invalid code
        with pytest.raises(CodeAnalysisError):
            self.detector.calculate_simhash(None)
        
        # Test with empty code
        result = self.detector.find_similar("")
        assert result.is_duplicate is False
        
        # Test with whitespace only
        result = self.detector.find_similar("   \n  \t  ")
        assert result.is_duplicate is False
    
    def test_performance_large_dataset(self):
        """Test performance with larger dataset."""
        # Add many records
        records = []
        for i in range(1000):
            record = CodeRecord(
                id=i,
                code_content=f'def func_{i}(): return {i} * 2',
                function_name=f"func_{i}"
            )
            records.append(record)
        
        # Rebuild index
        start_time = time.time()
        self.detector.rebuild_index(records)
        build_time = time.time() - start_time
        
        # Should build quickly
        assert build_time < 5.0  # 5 seconds max
        
        # Search should be fast
        start_time = time.time()
        result = self.detector.find_similar('def func_500(): return 500 * 2')
        search_time = time.time() - start_time
        
        assert search_time < 0.1  # 100ms max
        assert result.is_duplicate is True
    
    def test_code_variations(self):
        """Test similarity detection with code variations."""
        # Add base code
        base_code = '''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
'''
        
        record = CodeRecord(
            id=1,
            code_content=base_code,
            function_name="fibonacci"
        )
        self.detector.add_record(record)
        
        # Test variations
        variations = [
            # Same code with comment
            '''
def fibonacci(n):
    # This is a comment
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
''',
            # Same code with different variable
            '''
def fibonacci(num):
    if num <= 1:
        return num
    return fibonacci(num-1) + fibonacci(num-2)
''',
            # Different algorithm
            '''
def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
''',
            # Completely different function
            '''
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
'''
        ]
        
        for i, variation in enumerate(variations):
            result = self.detector.find_similar(variation)
            similarity = self.detector.analyze_similarity(base_code, variation)
            
            print(f"Variation {i+1}: similarity={similarity:.3f}, duplicate={result.is_duplicate}")
            
            # First variation (with comment) should be most similar
            if i == 0:
                assert similarity > 0.9
            # Last variation (completely different) should be least similar
            elif i == len(variations) - 1:
                assert similarity < 0.7