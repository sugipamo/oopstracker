"""
AST-based code tracking database manager.
Handles persistence for CodeUnit and AST-specific metadata.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Set

from .models import CodeRecord
from .ast_analyzer import CodeUnit


logger = logging.getLogger(__name__)


class ASTDatabaseManager:
    """
    Database manager for AST-based code tracking.
    Handles persistence of CodeRecord and CodeUnit data.
    """
    
    def __init__(self, db_path: str = "oopstracker_ast.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.connection = None
        self._initialize_database()
        logger.info(f"Initialized AST database: {db_path}")
    
    def _initialize_database(self):
        """Create database tables if they don't exist."""
        try:
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row  # Enable column access by name
            
            # Create tables
            self._create_tables()
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _create_tables(self):
        """Create database tables."""
        cursor = self.connection.cursor()
        
        # Main code records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ast_code_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_hash TEXT UNIQUE NOT NULL,
                code_content TEXT NOT NULL,
                function_name TEXT,
                file_path TEXT,
                timestamp TEXT NOT NULL,
                simhash TEXT,  -- Store as TEXT to handle large ints
                
                -- AST-specific fields
                unit_type TEXT NOT NULL,  -- 'function', 'class', 'module'
                start_line INTEGER,
                end_line INTEGER,
                complexity_score INTEGER,
                ast_structure TEXT,
                
                -- Metadata as JSON
                metadata TEXT
            )
        """)
        
        # Dependencies table (normalized)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ast_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_hash TEXT NOT NULL,
                dependency TEXT NOT NULL,
                
                FOREIGN KEY (code_hash) REFERENCES ast_code_records (code_hash),
                UNIQUE(code_hash, dependency)
            )
        """)
        
        # Database metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ast_database_info (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # File tracking table for incremental updates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ast_file_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT NOT NULL,
                last_modified TEXT NOT NULL,
                last_scanned TEXT NOT NULL,
                unit_count INTEGER DEFAULT 0
            )
        """)
        
        # Insert schema version
        cursor.execute("""
            INSERT OR REPLACE INTO ast_database_info (key, value)
            VALUES ('schema_version', '1.0')
        """)
        
        # Insert creation timestamp
        cursor.execute("""
            INSERT OR IGNORE INTO ast_database_info (key, value)
            VALUES ('created_at', ?)
        """, (datetime.now().isoformat(),))
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_code_hash ON ast_code_records(code_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_function_name ON ast_code_records(function_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_path ON ast_code_records(file_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_unit_type ON ast_code_records(unit_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_simhash ON ast_code_records(simhash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_tracking_path ON ast_file_tracking(file_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_tracking_hash ON ast_file_tracking(file_hash)")
        
        self.connection.commit()
        logger.debug("Database tables created successfully")
    
    def insert_record(self, record: CodeRecord, unit: CodeUnit) -> bool:
        """
        Insert a new code record and unit.
        
        Args:
            record: CodeRecord to insert
            unit: CodeUnit with AST data
            
        Returns:
            True if inserted successfully, False if already exists
        """
        try:
            cursor = self.connection.cursor()
            
            # Prepare metadata
            metadata_json = json.dumps(record.metadata) if record.metadata else None
            
            # Insert main record
            cursor.execute("""
                INSERT OR REPLACE INTO ast_code_records (
                    code_hash, code_content, function_name, file_path, timestamp,
                    simhash, unit_type, start_line, end_line, complexity_score,
                    ast_structure, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.code_hash,
                record.code_content,
                record.function_name,
                record.file_path,
                record.timestamp.isoformat() if record.timestamp else datetime.now().isoformat(),
                str(record.simhash) if record.simhash is not None else None,
                unit.type,
                unit.start_line,
                unit.end_line,
                unit.complexity_score,
                unit.ast_structure,
                metadata_json
            ))
            
            # Insert dependencies
            if unit.dependencies:
                cursor.execute("DELETE FROM ast_dependencies WHERE code_hash = ?", (record.code_hash,))
                
                for dependency in unit.dependencies:
                    cursor.execute("""
                        INSERT INTO ast_dependencies (code_hash, dependency)
                        VALUES (?, ?)
                    """, (record.code_hash, dependency))
            
            self.connection.commit()
            logger.debug(f"Inserted record: {record.code_hash[:16]}...")
            return True
            
        except sqlite3.IntegrityError as e:
            logger.warning(f"Record already exists: {record.code_hash[:16]}...")
            return False
        except Exception as e:
            logger.error(f"Failed to insert record: {e}")
            self.connection.rollback()
            return False
    
    def get_all_records(self) -> List[Tuple[CodeRecord, CodeUnit]]:
        """
        Get all records with their corresponding CodeUnits.
        
        Returns:
            List of (CodeRecord, CodeUnit) tuples
        """
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                SELECT 
                    code_hash, code_content, function_name, file_path, timestamp,
                    simhash, unit_type, start_line, end_line, complexity_score,
                    ast_structure, metadata
                FROM ast_code_records
                ORDER BY timestamp DESC
            """)
            
            records = []
            for row in cursor.fetchall():
                # Create CodeRecord
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                timestamp = datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None
                
                record = CodeRecord(
                    code_hash=row['code_hash'],
                    code_content=row['code_content'],
                    function_name=row['function_name'],
                    file_path=row['file_path'],
                    timestamp=timestamp,
                    simhash=int(row['simhash']) if row['simhash'] else None,
                    metadata=metadata
                )
                
                # Get dependencies
                deps_cursor = self.connection.cursor()
                deps_cursor.execute("""
                    SELECT dependency FROM ast_dependencies 
                    WHERE code_hash = ?
                """, (row['code_hash'],))
                dependencies = [dep_row[0] for dep_row in deps_cursor.fetchall()]
                
                # Create CodeUnit
                unit = CodeUnit(
                    name=row['function_name'] or 'module',
                    type=row['unit_type'],
                    source_code=row['code_content'],
                    start_line=row['start_line'],
                    end_line=row['end_line'],
                    file_path=row['file_path'],
                    ast_structure=row['ast_structure'],
                    complexity_score=row['complexity_score'],
                    dependencies=dependencies
                )
                
                records.append((record, unit))
            
            logger.debug(f"Retrieved {len(records)} records from database")
            return records
            
        except Exception as e:
            logger.error(f"Failed to get all records: {e}")
            return []
    
    def get_by_file_path(self, file_path: str) -> List[Tuple[CodeRecord, CodeUnit]]:
        """
        Get all records for a specific file.
        
        Args:
            file_path: File path to search for
            
        Returns:
            List of (CodeRecord, CodeUnit) tuples
        """
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                SELECT 
                    code_hash, code_content, function_name, file_path, timestamp,
                    simhash, unit_type, start_line, end_line, complexity_score,
                    ast_structure, metadata
                FROM ast_code_records
                WHERE file_path = ?
                ORDER BY start_line
            """, (file_path,))
            
            records = []
            for row in cursor.fetchall():
                # Similar to get_all_records but for specific file
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                timestamp = datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None
                
                record = CodeRecord(
                    code_hash=row['code_hash'],
                    code_content=row['code_content'],
                    function_name=row['function_name'],
                    file_path=row['file_path'],
                    timestamp=timestamp,
                    simhash=int(row['simhash']) if row['simhash'] else None,
                    metadata=metadata
                )
                
                # Get dependencies
                deps_cursor = self.connection.cursor()
                deps_cursor.execute("""
                    SELECT dependency FROM ast_dependencies 
                    WHERE code_hash = ?
                """, (row['code_hash'],))
                dependencies = [dep_row[0] for dep_row in deps_cursor.fetchall()]
                
                unit = CodeUnit(
                    name=row['function_name'] or 'module',
                    type=row['unit_type'],
                    source_code=row['code_content'],
                    start_line=row['start_line'],
                    end_line=row['end_line'],
                    file_path=row['file_path'],
                    ast_structure=row['ast_structure'],
                    complexity_score=row['complexity_score'],
                    dependencies=dependencies
                )
                
                records.append((record, unit))
            
            return records
            
        except Exception as e:
            logger.error(f"Failed to get records for file {file_path}: {e}")
            return []
    
    def delete_by_file_path(self, file_path: str) -> int:
        """
        Delete all records for a specific file.
        
        Args:
            file_path: File path to delete records for
            
        Returns:
            Number of deleted records
        """
        try:
            cursor = self.connection.cursor()
            
            # Get code_hashes to delete dependencies
            cursor.execute("SELECT code_hash FROM ast_code_records WHERE file_path = ?", (file_path,))
            code_hashes = [row[0] for row in cursor.fetchall()]
            
            # Delete dependencies
            for code_hash in code_hashes:
                cursor.execute("DELETE FROM ast_dependencies WHERE code_hash = ?", (code_hash,))
            
            # Delete main records
            cursor.execute("DELETE FROM ast_code_records WHERE file_path = ?", (file_path,))
            deleted_count = cursor.rowcount
            
            self.connection.commit()
            logger.info(f"Deleted {deleted_count} records for file: {file_path}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete records for file {file_path}: {e}")
            self.connection.rollback()
            return 0
    
    def clear_all(self):
        """Clear all data from the database."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM ast_dependencies")
            cursor.execute("DELETE FROM ast_code_records")
            self.connection.commit()
            logger.info("Cleared all data from database")
            
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            self.connection.rollback()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            cursor = self.connection.cursor()
            
            # Total records
            cursor.execute("SELECT COUNT(*) FROM ast_code_records")
            total_records = cursor.fetchone()[0]
            
            # Records by type
            cursor.execute("""
                SELECT unit_type, COUNT(*) 
                FROM ast_code_records 
                GROUP BY unit_type
            """)
            type_counts = dict(cursor.fetchall())
            
            # Unique files
            cursor.execute("SELECT COUNT(DISTINCT file_path) FROM ast_code_records WHERE file_path IS NOT NULL")
            unique_files = cursor.fetchone()[0]
            
            # Average complexity
            cursor.execute("SELECT AVG(complexity_score) FROM ast_code_records WHERE complexity_score IS NOT NULL")
            avg_complexity = cursor.fetchone()[0] or 0
            
            # Database size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size_bytes = cursor.fetchone()[0]
            
            # Count deleted files (files in DB but not on disk)
            existing_files = self.get_existing_files()
            deleted_count = sum(1 for f in existing_files if not Path(f).exists())
            
            return {
                "total_units": total_records,  # For compatibility with CLI
                "total_records": total_records,
                "functions": type_counts.get("function", 0),
                "classes": type_counts.get("class", 0),
                "modules": type_counts.get("module", 0),
                "unique_files": unique_files,
                "deleted_files": deleted_count,
                "average_complexity": round(avg_complexity, 2),
                "database_size_mb": round(db_size_bytes / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.debug("Database connection closed")
    
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
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT file_hash FROM ast_file_tracking 
                WHERE file_path = ?
            """, (file_path,))
            
            result = cursor.fetchone()
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Failed to get file hash: {e}")
            return None
    
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
        try:
            cursor = self.connection.cursor()
            
            # Get file modification time
            file_mtime = datetime.fromtimestamp(Path(file_path).stat().st_mtime).isoformat()
            scan_time = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO ast_file_tracking 
                (file_path, file_hash, last_modified, last_scanned, unit_count)
                VALUES (?, ?, ?, ?, ?)
            """, (file_path, file_hash, file_mtime, scan_time, unit_count))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update file tracking: {e}")
            self.connection.rollback()
            return False
    
    def get_changed_files(self, file_paths: List[str]) -> List[str]:
        """
        Get list of files that have changed since last scan.
        
        Args:
            file_paths: List of file paths to check
            
        Returns:
            List of changed file paths
        """
        import hashlib
        
        changed_files = []
        
        for file_path in file_paths:
            try:
                # Calculate current file hash
                with open(file_path, 'rb') as f:
                    current_hash = hashlib.sha256(f.read()).hexdigest()
                
                # Get stored hash
                stored_hash = self.get_file_hash(file_path)
                
                # If no stored hash or hash differs, file has changed
                if stored_hash is None or stored_hash != current_hash:
                    changed_files.append(file_path)
                    
            except Exception as e:
                logger.warning(f"Error checking file {file_path}: {e}")
                # Assume changed if we can't check
                changed_files.append(file_path)
        
        return changed_files
    
    def remove_file_records(self, file_path: str) -> int:
        """
        Remove all records for a file (when file is deleted or changed).
        
        Args:
            file_path: File path to remove records for
            
        Returns:
            Number of records removed
        """
        try:
            # First delete from file tracking
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM ast_file_tracking WHERE file_path = ?", (file_path,))
            
            # Then delete code records
            deleted = self.delete_by_file_path(file_path)
            
            self.connection.commit()
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to remove file records: {e}")
            self.connection.rollback()
            return 0
    
    def get_existing_files(self) -> Set[str]:
        """
        Get set of all file paths currently tracked in database.
        
        Returns:
            Set of file paths
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT DISTINCT file_path FROM ast_code_records WHERE file_path IS NOT NULL")
            
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
        tracked_files = self.get_existing_files()
        deleted_files = tracked_files - current_files
        
        if deleted_files:
            logger.info(f"Found {len(deleted_files)} deleted files in database")
            # For now, just log them - could add a 'deleted' flag later
            for file_path in deleted_files:
                logger.debug(f"  Deleted: {file_path}")
        
        return list(deleted_files)