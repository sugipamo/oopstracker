"""
Tests for OOPStracker core functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path

from oopstracker.core import CodeMemory, CodeNormalizer, CodeSimilarityDetector
from oopstracker.models import CodeRecord
from oopstracker.exceptions import ValidationError, DatabaseError


class TestCodeNormalizer:
    """Test code normalization functionality."""
    
    def test_normalize_simple_code(self):
        normalizer = CodeNormalizer()
        
        code = '''
def hello():
    # This is a comment
    print("Hello, world!")
'''
        
        normalized = normalizer.normalize_code(code)
        assert "# This is a comment" not in normalized
        assert "hello" in normalized
        assert "print" in normalized
    
    def test_normalize_handles_syntax_error(self):
        normalizer = CodeNormalizer()
        
        # Invalid Python syntax
        code = "def hello( invalid syntax"
        
        # Should not raise exception, fallback to basic normalization
        normalized = normalizer.normalize_code(code)
        assert normalized is not None
    
    def test_normalize_removes_extra_whitespace(self):
        normalizer = CodeNormalizer()
        
        code = '''
        
        def   hello():
            print("Hello")
        
        '''
        
        normalized = normalizer.normalize_code(code)
        assert "  " not in normalized  # No double spaces
        assert normalized.strip() == normalized  # No leading/trailing whitespace


class TestCodeSimilarityDetector:
    """Test code similarity detection."""
    
    def test_exact_match(self):
        detector = CodeSimilarityDetector()
        
        code1 = 'def hello(): print("Hello")'
        code2 = 'def hello(): print("Hello")'
        
        similarity = detector.analyze_similarity(code1, code2)
        assert similarity == 1.0
        
        assert detector.is_duplicate(code1, code2)
    
    def test_different_code(self):
        detector = CodeSimilarityDetector()
        
        code1 = 'def hello(): print("Hello")'
        code2 = 'def goodbye(): print("Goodbye")'
        
        similarity = detector.analyze_similarity(code1, code2)
        assert similarity == 0.0
        
        assert not detector.is_duplicate(code1, code2)
    
    def test_comments_ignored(self):
        detector = CodeSimilarityDetector()
        
        code1 = '''
def hello():
    print("Hello")
'''
        
        code2 = '''
def hello():
    # This is a comment
    print("Hello")
'''
        
        similarity = detector.analyze_similarity(code1, code2)
        assert similarity == 1.0


class TestCodeMemory:
    """Test main CodeMemory functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.memory = CodeMemory(db_path=self.db_path)
    
    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_register_code(self):
        """Test registering new code."""
        code = 'def hello(): print("Hello")'
        
        record = self.memory.register(code, function_name="hello")
        
        assert record.id is not None
        assert record.code_hash is not None
        assert record.code_content == code
        assert record.function_name == "hello"
        assert record.timestamp is not None
    
    def test_register_empty_code_raises_error(self):
        """Test that registering empty code raises error."""
        with pytest.raises(ValidationError):
            self.memory.register("")
        
        with pytest.raises(ValidationError):
            self.memory.register("   ")
    
    def test_duplicate_detection(self):
        """Test duplicate code detection."""
        code1 = 'def hello(): print("Hello")'
        code2 = 'def hello(): print("Hello")'
        
        # Register first code
        self.memory.register(code1)
        
        # Check if second code is duplicate
        result = self.memory.is_duplicate(code2)
        
        assert result.is_duplicate
        assert result.similarity_score == 1.0
        assert len(result.matched_records) == 1
        assert result.matched_records[0].code_content == code1
    
    def test_non_duplicate_detection(self):
        """Test non-duplicate code detection."""
        code1 = 'def hello(): print("Hello")'
        code2 = 'def goodbye(): print("Goodbye")'
        
        # Register first code
        self.memory.register(code1)
        
        # Check if second code is duplicate
        result = self.memory.is_duplicate(code2)
        
        assert not result.is_duplicate
        assert result.similarity_score == 0.0
        assert len(result.matched_records) == 0
    
    def test_get_all_records(self):
        """Test getting all records."""
        code1 = 'def hello(): print("Hello")'
        code2 = 'def goodbye(): print("Goodbye")'
        
        # Initially empty
        records = self.memory.get_all_records()
        assert len(records) == 0
        
        # Register codes
        self.memory.register(code1)
        self.memory.register(code2)
        
        # Should have 2 records
        records = self.memory.get_all_records()
        assert len(records) == 2
        
        # Check content
        contents = [r.code_content for r in records]
        assert code1 in contents
        assert code2 in contents
    
    def test_clear_memory(self):
        """Test clearing memory."""
        code = 'def hello(): print("Hello")'
        
        # Register code
        self.memory.register(code)
        
        # Verify it's there
        records = self.memory.get_all_records()
        assert len(records) == 1
        
        # Clear memory
        self.memory.clear_memory()
        
        # Verify it's gone
        records = self.memory.get_all_records()
        assert len(records) == 0
    
    def test_register_with_metadata(self):
        """Test registering code with metadata."""
        code = 'def hello(): print("Hello")'
        metadata = {"author": "test_user", "version": "1.0"}
        
        record = self.memory.register(
            code,
            function_name="hello",
            file_path="test.py",
            metadata=metadata
        )
        
        assert record.function_name == "hello"
        assert record.file_path == "test.py"
        assert record.metadata == metadata
        
        # Verify it's stored correctly
        records = self.memory.get_all_records()
        assert len(records) == 1
        assert records[0].metadata == metadata