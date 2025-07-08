"""
Tests for OOPStracker models.
"""

import pytest
from datetime import datetime
from oopstracker.models import CodeRecord, SimilarityResult, DatabaseConfig


class TestCodeRecord:
    """Test CodeRecord model."""
    
    def test_create_empty_record(self):
        """Test creating empty record."""
        record = CodeRecord()
        
        assert record.id is None
        assert record.code_hash is None
        assert record.code_content is None
        assert record.timestamp is not None
        assert record.metadata == {}
    
    def test_create_record_with_data(self):
        """Test creating record with data."""
        timestamp = datetime.now()
        metadata = {"test": "value"}
        
        record = CodeRecord(
            id=1,
            code_content="def hello(): pass",
            function_name="hello",
            file_path="test.py",
            timestamp=timestamp,
            metadata=metadata
        )
        
        assert record.id == 1
        assert record.code_content == "def hello(): pass"
        assert record.function_name == "hello"
        assert record.file_path == "test.py"
        assert record.timestamp == timestamp
        assert record.metadata == metadata
    
    def test_generate_hash(self):
        """Test hash generation."""
        record = CodeRecord(code_content="def hello(): pass")
        
        hash_value = record.generate_hash()
        
        assert hash_value is not None
        assert len(hash_value) == 64  # SHA-256 hex length
        assert record.code_hash == hash_value
    
    def test_generate_hash_with_normalized_code(self):
        """Test hash generation with normalized code."""
        record = CodeRecord(
            code_content="def hello(): pass",
            normalized_code="def hello():pass"
        )
        
        hash_value = record.generate_hash()
        
        # Should use normalized code for hash
        assert hash_value is not None
        assert record.code_hash == hash_value
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        timestamp = datetime.now()
        record = CodeRecord(
            id=1,
            code_content="def hello(): pass",
            function_name="hello",
            timestamp=timestamp,
            metadata={"test": "value"}
        )
        record.generate_hash()
        
        data = record.to_dict()
        
        assert data["id"] == 1
        assert data["code_content"] == "def hello(): pass"
        assert data["function_name"] == "hello"
        assert data["timestamp"] == timestamp.isoformat()
        assert data["metadata"] == {"test": "value"}
        assert data["code_hash"] is not None
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        timestamp = datetime.now()
        data = {
            "id": 1,
            "code_content": "def hello(): pass",
            "function_name": "hello",
            "timestamp": timestamp.isoformat(),
            "metadata": {"test": "value"}
        }
        
        record = CodeRecord.from_dict(data)
        
        assert record.id == 1
        assert record.code_content == "def hello(): pass"
        assert record.function_name == "hello"
        assert record.timestamp == timestamp
        assert record.metadata == {"test": "value"}


class TestSimilarityResult:
    """Test SimilarityResult model."""
    
    def test_create_result(self):
        """Test creating similarity result."""
        record = CodeRecord(code_content="def hello(): pass")
        
        result = SimilarityResult(
            is_duplicate=True,
            similarity_score=0.95,
            matched_records=[record]
        )
        
        assert result.is_duplicate is True
        assert result.similarity_score == 0.95
        assert len(result.matched_records) == 1
        assert result.matched_records[0] == record
        assert result.analysis_method == "sha256"
        assert result.threshold == 1.0
    
    def test_create_result_with_defaults(self):
        """Test creating result with defaults."""
        result = SimilarityResult(
            is_duplicate=False,
            similarity_score=0.0,
            matched_records=[]
        )
        
        assert result.is_duplicate is False
        assert result.similarity_score == 0.0
        assert result.matched_records == []
        assert result.analysis_method == "sha256"
        assert result.threshold == 1.0
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        record = CodeRecord(code_content="def hello(): pass")
        
        result = SimilarityResult(
            is_duplicate=True,
            similarity_score=0.95,
            matched_records=[record],
            analysis_method="simhash",
            threshold=0.8
        )
        
        data = result.to_dict()
        
        assert data["is_duplicate"] is True
        assert data["similarity_score"] == 0.95
        assert len(data["matched_records"]) == 1
        assert data["analysis_method"] == "simhash"
        assert data["threshold"] == 0.8
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        record_data = {
            "code_content": "def hello(): pass",
            "function_name": "hello"
        }
        
        data = {
            "is_duplicate": True,
            "similarity_score": 0.95,
            "matched_records": [record_data],
            "analysis_method": "simhash",
            "threshold": 0.8
        }
        
        result = SimilarityResult.from_dict(data)
        
        assert result.is_duplicate is True
        assert result.similarity_score == 0.95
        assert len(result.matched_records) == 1
        assert result.matched_records[0].code_content == "def hello(): pass"
        assert result.analysis_method == "simhash"
        assert result.threshold == 0.8


class TestDatabaseConfig:
    """Test DatabaseConfig model."""
    
    def test_create_config_with_defaults(self):
        """Test creating config with defaults."""
        config = DatabaseConfig()
        
        assert config.db_path == "oopstracker.db"
        assert config.create_tables is True
        assert config.backup_enabled is True
        assert config.backup_interval == 3600
        assert config.max_records is None
    
    def test_create_config_with_values(self):
        """Test creating config with custom values."""
        config = DatabaseConfig(
            db_path="custom.db",
            create_tables=False,
            backup_enabled=False,
            backup_interval=7200,
            max_records=1000
        )
        
        assert config.db_path == "custom.db"
        assert config.create_tables is False
        assert config.backup_enabled is False
        assert config.backup_interval == 7200
        assert config.max_records == 1000
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        config = DatabaseConfig(
            db_path="test.db",
            max_records=500
        )
        
        data = config.to_dict()
        
        assert data["db_path"] == "test.db"
        assert data["create_tables"] is True
        assert data["backup_enabled"] is True
        assert data["backup_interval"] == 3600
        assert data["max_records"] == 500