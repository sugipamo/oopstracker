"""
AST-based code tracking database manager.
Handles persistence for CodeUnit and AST-specific metadata.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Set

from .models import CodeRecord
from .ast_analyzer import CodeUnit
from .database import (
    DatabaseConnectionManager,
    SchemaManager,
    FileTrackingRepository,
    CodeRecordRepository
)

logger = logging.getLogger(__name__)


class ASTDatabaseManager:
    """
    Database manager for AST-based code tracking.
    Provides a unified interface for all database operations.
    """
    
    def __init__(self, db_path: str = "oopstracker_ast.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.connection_manager = DatabaseConnectionManager(db_path)
        self.schema_manager = SchemaManager(self.connection_manager)
        self.file_tracking = FileTrackingRepository(self.connection_manager)
        self.code_records = CodeRecordRepository(self.connection_manager)
        
        self._initialize_database()
        logger.info(f"Initialized AST database: {db_path}")
    
    def _initialize_database(self):
        """Initialize database schema."""
        try:
            self.schema_manager.initialize_schema()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    @property
    def connection(self):
        """Get database connection for backward compatibility."""
        return self.connection_manager.connection
    
    def insert_record(self, record: CodeRecord, unit: CodeUnit) -> bool:
        """
        Insert a new code record and unit.
        
        Args:
            record: CodeRecord to insert
            unit: CodeUnit with AST data
            
        Returns:
            True if inserted successfully, False if already exists
        """
        return self.code_records.insert_record(record, unit)
    
    def get_all_records(self) -> List[Tuple[CodeRecord, CodeUnit]]:
        """
        Get all records with their corresponding CodeUnits.
        
        Returns:
            List of (CodeRecord, CodeUnit) tuples
        """
        return self.code_records.get_all_records()
    
    def get_by_file_path(self, file_path: str) -> List[Tuple[CodeRecord, CodeUnit]]:
        """
        Get all records for a specific file.
        
        Args:
            file_path: File path to search for
            
        Returns:
            List of (CodeRecord, CodeUnit) tuples
        """
        return self.code_records.get_by_file_path(file_path)
    
    def delete_by_file_path(self, file_path: str) -> int:
        """
        Delete all records for a specific file.
        
        Args:
            file_path: File path to delete records for
            
        Returns:
            Number of deleted records
        """
        return self.code_records.delete_by_file_path(file_path)
    
    def clear_all(self):
        """Clear all data from the database."""
        self.code_records.clear_all()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            # Get basic statistics from code records
            stats = self.code_records.get_statistics()
            
            # Add database size
            cursor = self.connection_manager.execute(
                "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()"
            )
            db_size_bytes = cursor.fetchone()[0]
            stats['database_size_mb'] = round(db_size_bytes / (1024 * 1024), 2)
            
            # Add compatibility field
            stats['total_units'] = stats.get('total_records', 0)
            
            # Count deleted files
            existing_files = self.get_existing_files()
            stats['deleted_files'] = sum(1 for f in existing_files if not Path(f).exists())
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def close(self):
        """Close database connection."""
        self.connection_manager.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def get_file_hash(self, file_path: str) -> Optional[str]:
        """
        Get stored file hash for a given file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File hash if exists, None otherwise
        """
        return self.file_tracking.get_file_hash(file_path)
    
    def update_file_tracking(self, file_path: str, file_hash: str, unit_count: int = 0) -> bool:
        """
        Update file tracking information.
        
        Args:
            file_path: Path to the file
            file_hash: Hash of the file contents
            unit_count: Number of code units in the file
            
        Returns:
            True if updated successfully
        """
        return self.file_tracking.update_file_tracking(file_path, file_hash, unit_count)
    
    def get_changed_files(self, file_paths: List[str]) -> List[str]:
        """
        Get list of files that have changed since last scan.
        
        Args:
            file_paths: List of file paths to check
            
        Returns:
            List of changed file paths
        """
        return self.file_tracking.get_changed_files(file_paths)
    
    def remove_file_records(self, file_path: str) -> int:
        """
        Remove all records for a file (when file is deleted or changed).
        
        Args:
            file_path: File path to remove records for
            
        Returns:
            Number of records removed
        """
        try:
            # Remove from file tracking
            self.file_tracking.remove_file_tracking(file_path)
            
            # Delete code records
            return self.delete_by_file_path(file_path)
            
        except Exception as e:
            logger.error(f"Failed to remove file records: {e}")
            return 0
    
    def get_existing_files(self) -> Set[str]:
        """
        Get set of all file paths currently tracked in database.
        
        Returns:
            Set of file paths
        """
        try:
            cursor = self.connection_manager.execute(
                "SELECT DISTINCT file_path FROM ast_code_records WHERE file_path IS NOT NULL"
            )
            return {row[0] for row in cursor.fetchall()}
            
        except Exception as e:
            logger.error(f"Failed to get existing files: {e}")
            return set()
    
    def check_and_mark_deleted_files(self, current_files: Set[str]) -> List[str]:
        """
        Check which tracked files no longer exist and optionally mark them.
        
        Args:
            current_files: Set of currently existing file paths
            
        Returns:
            List of deleted file paths
        """
        return self.file_tracking.check_deleted_files(current_files)