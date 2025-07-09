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
from .simhash_detector import SimHashSimilarityDetector


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
                simhash TEXT
            )
        ''')
        
        # Add simhash column if it doesn't exist (for existing databases)
        try:
            conn.execute('ALTER TABLE code_records ADD COLUMN simhash TEXT')
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
                    str(record.simhash) if record.simhash is not None else None
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
    
    def find_by_simhash(self, simhash: int) -> List[CodeRecord]:
        """Find code records with exact SimHash match."""
        try:
            with sqlite3.connect(self.config.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, code_hash, code_content, normalized_code, function_name, 
                           file_path, timestamp, metadata, simhash
                    FROM code_records 
                    WHERE simhash = ?
                ''', (str(simhash),))
                
                return [self._row_to_record(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to find records by simhash: {e}")
    
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
            simhash=int(row[8]) if len(row) > 8 and row[8] is not None else None
        )




class CodeMemory:
    """Main class for code memory management using SimHash-based similarity detection."""
    
    def __init__(self, db_path: str = "oopstracker.db", threshold: int = 10):
        self.config = DatabaseConfig(db_path=db_path)
        self.db_manager = DatabaseManager(self.config)
        self.similarity_detector = SimHashSimilarityDetector(threshold=threshold)
        self.normalizer = CodeNormalizer()
        self.logger = logging.getLogger(__name__)
        
        # Load existing records into SimHash detector
        self._load_existing_records()
    
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
            
            # Generate hash and SimHash
            record.generate_hash()
            record.simhash = self.similarity_detector.calculate_simhash(code)
            
            # Insert into database
            self.db_manager.insert_record(record)
            
            # Add to SimHash detector
            self.similarity_detector.add_record(record)
            
            self.logger.info(f"Registered code record with hash: {record.code_hash}")
            return record
            
        except Exception as e:
            self.logger.error(f"Failed to register code: {e}")
            raise
    
    def is_duplicate(self, code: str) -> SimilarityResult:
        """Check if code is a duplicate of existing code using SimHash similarity."""
        if not code or not code.strip():
            raise ValidationError("Code content cannot be empty")
        
        try:
            # Use SimHash for similarity detection
            result = self.similarity_detector.find_similar(code)
            self.logger.info(f"SimHash duplicate check result: {result.is_duplicate} (score: {result.similarity_score})")
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
    
    def _load_existing_records(self):
        """Load existing records from database into SimHash detector."""
        try:
            records = self.db_manager.get_all_records()
            for record in records:
                if record.simhash is None:
                    # Calculate SimHash for records that don't have it
                    record.simhash = self.similarity_detector.calculate_simhash(record.code_content)
                    # Update record in database
                    self.db_manager.insert_record(record)
                
                # Add to SimHash detector
                self.similarity_detector.add_record(record)
            
            self.logger.info(f"Loaded {len(records)} existing records into SimHash detector")
            
        except Exception as e:
            self.logger.warning(f"Failed to load existing records: {e}")
            # Continue anyway - this is not critical