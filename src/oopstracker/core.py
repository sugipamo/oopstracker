"""
Core functionality for OOPStracker.
"""

import ast
import hashlib
import re
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from .models import CodeRecord, SimilarityResult, DatabaseConfig
from .exceptions import DatabaseError, ValidationError, CodeAnalysisError


class CodeNormalizer:
    """Normalizes code for similarity comparison."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def normalize_code(self, code: str) -> str:
        """Normalize code by removing comments, extra whitespace, and standardizing format."""
        try:
            # Remove comments
            code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
            
            # Parse and reformat with AST
            tree = ast.parse(code)
            normalized = ast.unparse(tree)
            
            # Remove extra whitespace
            normalized = re.sub(r'\s+', ' ', normalized)
            normalized = normalized.strip()
            
            return normalized
            
        except SyntaxError as e:
            self.logger.warning(f"Code normalization failed due to syntax error: {e}")
            # Fallback to basic normalization
            return self._basic_normalize(code)
        except Exception as e:
            self.logger.error(f"Code normalization failed: {e}")
            raise CodeAnalysisError(f"Failed to normalize code: {e}")
    
    def _basic_normalize(self, code: str) -> str:
        """Basic normalization fallback."""
        # Remove comments
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        
        # Remove extra whitespace
        code = re.sub(r'\s+', ' ', code)
        code = code.strip()
        
        return code


class DatabaseManager:
    """Manages SQLite database operations."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize database and create tables if needed."""
        try:
            Path(self.config.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.config.db_path) as conn:
                if self.config.create_tables:
                    self._create_tables(conn)
                    
        except sqlite3.Error as e:
            raise DatabaseError(f"Database initialization failed: {e}")
    
    def _create_tables(self, conn: sqlite3.Connection):
        """Create database tables."""
        # Create table with all columns
        conn.execute('''
            CREATE TABLE IF NOT EXISTS code_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_hash TEXT NOT NULL UNIQUE,
                code_content TEXT NOT NULL,
                normalized_code TEXT,
                function_name TEXT,
                file_path TEXT,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                simhash INTEGER
            )
        ''')
        
        # Add simhash column if it doesn't exist (for existing databases)
        try:
            conn.execute('ALTER TABLE code_records ADD COLUMN simhash INTEGER')
        except sqlite3.OperationalError:
            # Column already exists, ignore
            pass
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_code_hash ON code_records(code_hash)
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON code_records(timestamp)
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_simhash ON code_records(simhash)
        ''')
        
        conn.commit()
    
    def insert_record(self, record: CodeRecord) -> int:
        """Insert a code record into the database."""
        try:
            with sqlite3.connect(self.config.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO code_records 
                    (code_hash, code_content, normalized_code, function_name, file_path, timestamp, metadata, simhash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record.code_hash,
                    record.code_content,
                    record.normalized_code,
                    record.function_name,
                    record.file_path,
                    record.timestamp.isoformat(),
                    str(record.metadata) if record.metadata else None,
                    record.simhash
                ))
                
                record.id = cursor.lastrowid
                conn.commit()
                return record.id
                
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to insert record: {e}")
    
    def find_by_hash(self, code_hash: str) -> Optional[CodeRecord]:
        """Find a code record by hash."""
        try:
            with sqlite3.connect(self.config.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, code_hash, code_content, normalized_code, function_name, 
                           file_path, timestamp, metadata, simhash
                    FROM code_records 
                    WHERE code_hash = ?
                ''', (code_hash,))
                
                row = cursor.fetchone()
                if row:
                    return self._row_to_record(row)
                return None
                
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to find record by hash: {e}")
    
    def find_similar(self, code_hash: str, threshold: float = 1.0) -> List[CodeRecord]:
        """Find similar code records."""
        # For now, only exact matches (threshold = 1.0)
        # TODO: Implement fuzzy matching for threshold < 1.0
        if threshold >= 1.0:
            record = self.find_by_hash(code_hash)
            return [record] if record else []
        else:
            # TODO: Implement SimHash or other similarity matching
            return []
    
    def get_all_records(self) -> List[CodeRecord]:
        """Get all code records."""
        try:
            with sqlite3.connect(self.config.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, code_hash, code_content, normalized_code, function_name, 
                           file_path, timestamp, metadata, simhash
                    FROM code_records 
                    ORDER BY timestamp DESC
                ''')
                
                return [self._row_to_record(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to get all records: {e}")
    
    def _row_to_record(self, row: Tuple) -> CodeRecord:
        """Convert database row to CodeRecord."""
        return CodeRecord(
            id=row[0],
            code_hash=row[1],
            code_content=row[2],
            normalized_code=row[3],
            function_name=row[4],
            file_path=row[5],
            timestamp=datetime.fromisoformat(row[6]),
            metadata=eval(row[7]) if row[7] else {},
            simhash=row[8] if len(row) > 8 else None
        )


class CodeSimilarityDetector:
    """Detects code similarity using various methods."""
    
    def __init__(self, threshold: float = 1.0):
        self.threshold = threshold
        self.normalizer = CodeNormalizer()
        self.logger = logging.getLogger(__name__)
    
    def analyze_similarity(self, code1: str, code2: str) -> float:
        """Analyze similarity between two code snippets."""
        try:
            normalized1 = self.normalizer.normalize_code(code1)
            normalized2 = self.normalizer.normalize_code(code2)
            
            # Simple exact match for now
            if normalized1 == normalized2:
                return 1.0
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Similarity analysis failed: {e}")
            return 0.0
    
    def is_duplicate(self, code1: str, code2: str) -> bool:
        """Check if two code snippets are duplicates."""
        similarity = self.analyze_similarity(code1, code2)
        return similarity >= self.threshold


class CodeMemory:
    """Main class for code memory management."""
    
    def __init__(self, db_path: str = "oopstracker.db", threshold: float = 1.0):
        self.config = DatabaseConfig(db_path=db_path)
        self.db_manager = DatabaseManager(self.config)
        self.similarity_detector = CodeSimilarityDetector(threshold=threshold)
        self.normalizer = CodeNormalizer()
        self.logger = logging.getLogger(__name__)
    
    def register(self, code: str, function_name: Optional[str] = None, 
                 file_path: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> CodeRecord:
        """Register a new code snippet."""
        if not code or not code.strip():
            raise ValidationError("Code content cannot be empty")
        
        try:
            # Normalize and hash the code
            normalized_code = self.normalizer.normalize_code(code)
            
            # Create record
            record = CodeRecord(
                code_content=code,
                normalized_code=normalized_code,
                function_name=function_name,
                file_path=file_path,
                metadata=metadata or {}
            )
            
            # Generate hash
            record.generate_hash()
            
            # Insert into database
            self.db_manager.insert_record(record)
            
            self.logger.info(f"Registered code record with hash: {record.code_hash}")
            return record
            
        except Exception as e:
            self.logger.error(f"Failed to register code: {e}")
            raise
    
    def is_duplicate(self, code: str) -> SimilarityResult:
        """Check if code is a duplicate of existing code."""
        if not code or not code.strip():
            raise ValidationError("Code content cannot be empty")
        
        try:
            # Normalize and hash the code
            normalized_code = self.normalizer.normalize_code(code)
            code_hash = hashlib.sha256(normalized_code.encode('utf-8')).hexdigest()
            
            # Find similar records
            matched_records = self.db_manager.find_similar(
                code_hash, 
                threshold=self.similarity_detector.threshold
            )
            
            # Determine if it's a duplicate
            is_duplicate = len(matched_records) > 0
            similarity_score = 1.0 if is_duplicate else 0.0
            
            result = SimilarityResult(
                is_duplicate=is_duplicate,
                similarity_score=similarity_score,
                matched_records=matched_records,
                analysis_method="sha256",
                threshold=self.similarity_detector.threshold
            )
            
            self.logger.info(f"Duplicate check result: {is_duplicate} (score: {similarity_score})")
            return result
            
        except Exception as e:
            self.logger.error(f"Duplicate check failed: {e}")
            raise
    
    def get_all_records(self) -> List[CodeRecord]:
        """Get all stored code records."""
        return self.db_manager.get_all_records()
    
    def clear_memory(self):
        """Clear all stored code records."""
        try:
            Path(self.config.db_path).unlink(missing_ok=True)
            self.db_manager._init_database()
            self.logger.info("Memory cleared successfully")
        except Exception as e:
            self.logger.error(f"Failed to clear memory: {e}")
            raise DatabaseError(f"Failed to clear memory: {e}")