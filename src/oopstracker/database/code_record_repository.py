"""
Repository for code record operations.
Handles CRUD operations for code records and units.
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple

from ..models import CodeRecord
from ..ast_analyzer import CodeUnit

logger = logging.getLogger(__name__)


class CodeRecordRepository:
    """
    Repository for code record CRUD operations.
    """
    
    def __init__(self, connection_manager):
        """
        Initialize code record repository.
        
        Args:
            connection_manager: DatabaseConnectionManager instance
        """
        self.connection_manager = connection_manager
    
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
            with self.connection_manager.transaction():
                # Insert main record
                self._insert_code_record(record, unit)
                
                # Insert dependencies
                self._insert_dependencies(record.code_hash, unit.dependencies)
                
            logger.debug(f"Inserted record: {record.code_hash[:16]}...")
            return True
            
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                logger.warning(f"Record already exists: {record.code_hash[:16]}...")
                return False
            logger.error(f"Failed to insert record: {e}")
            return False
    
    def _insert_code_record(self, record: CodeRecord, unit: CodeUnit):
        """Insert the main code record."""
        metadata_json = json.dumps(record.metadata) if record.metadata else None
        
        self.connection_manager.execute("""
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
    
    def _insert_dependencies(self, code_hash: str, dependencies: List[str]):
        """Insert dependencies for a code record."""
        if not dependencies:
            return
            
        # Delete existing dependencies
        self.connection_manager.execute(
            "DELETE FROM ast_dependencies WHERE code_hash = ?",
            (code_hash,)
        )
        
        # Insert new dependencies
        for dependency in dependencies:
            self.connection_manager.execute("""
                INSERT INTO ast_dependencies (code_hash, dependency)
                VALUES (?, ?)
            """, (code_hash, dependency))
    
    def get_all_records(self) -> List[Tuple[CodeRecord, CodeUnit]]:
        """
        Get all records with their corresponding CodeUnits.
        
        Returns:
            List of (CodeRecord, CodeUnit) tuples
        """
        try:
            cursor = self.connection_manager.execute("""
                SELECT 
                    code_hash, code_content, function_name, file_path, timestamp,
                    simhash, unit_type, start_line, end_line, complexity_score,
                    ast_structure, metadata
                FROM ast_code_records
                ORDER BY timestamp DESC
            """)
            
            records = []
            for row in cursor.fetchall():
                record, unit = self._row_to_record_and_unit(row)
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
            cursor = self.connection_manager.execute("""
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
                record, unit = self._row_to_record_and_unit(row)
                records.append((record, unit))
            
            return records
            
        except Exception as e:
            logger.error(f"Failed to get records for file {file_path}: {e}")
            return []
    
    def _row_to_record_and_unit(self, row: Any) -> Tuple[CodeRecord, CodeUnit]:
        """Convert database row to CodeRecord and CodeUnit."""
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
        dependencies = self._get_dependencies(row['code_hash'])
        
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
        
        return record, unit
    
    def _get_dependencies(self, code_hash: str) -> List[str]:
        """Get dependencies for a code record."""
        cursor = self.connection_manager.execute("""
            SELECT dependency FROM ast_dependencies 
            WHERE code_hash = ?
        """, (code_hash,))
        return [row['dependency'] for row in cursor.fetchall()]
    
    def delete_by_file_path(self, file_path: str) -> int:
        """
        Delete all records for a specific file.
        
        Args:
            file_path: File path to delete records for
            
        Returns:
            Number of deleted records
        """
        try:
            with self.connection_manager.transaction():
                # Get code_hashes to delete dependencies
                cursor = self.connection_manager.execute(
                    "SELECT code_hash FROM ast_code_records WHERE file_path = ?",
                    (file_path,)
                )
                code_hashes = [row['code_hash'] for row in cursor.fetchall()]
                
                # Delete dependencies
                for code_hash in code_hashes:
                    self.connection_manager.execute(
                        "DELETE FROM ast_dependencies WHERE code_hash = ?",
                        (code_hash,)
                    )
                
                # Delete main records
                cursor = self.connection_manager.execute(
                    "DELETE FROM ast_code_records WHERE file_path = ?",
                    (file_path,)
                )
                deleted_count = cursor.rowcount
            
            logger.info(f"Deleted {deleted_count} records for file: {file_path}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete records for file {file_path}: {e}")
            return 0
    
    def clear_all(self):
        """Clear all data from the database."""
        try:
            with self.connection_manager.transaction():
                self.connection_manager.execute("DELETE FROM ast_dependencies")
                self.connection_manager.execute("DELETE FROM ast_code_records")
            
            logger.info("Cleared all data from database")
            
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get repository statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            stats = {}
            
            # Total records
            cursor = self.connection_manager.execute("SELECT COUNT(*) FROM ast_code_records")
            stats['total_records'] = cursor.fetchone()[0]
            
            # Records by type
            cursor = self.connection_manager.execute("""
                SELECT unit_type, COUNT(*) 
                FROM ast_code_records 
                GROUP BY unit_type
            """)
            type_counts = dict(cursor.fetchall())
            stats.update({
                'functions': type_counts.get('function', 0),
                'classes': type_counts.get('class', 0),
                'modules': type_counts.get('module', 0)
            })
            
            # Unique files
            cursor = self.connection_manager.execute(
                "SELECT COUNT(DISTINCT file_path) FROM ast_code_records WHERE file_path IS NOT NULL"
            )
            stats['unique_files'] = cursor.fetchone()[0]
            
            # Average complexity
            cursor = self.connection_manager.execute(
                "SELECT AVG(complexity_score) FROM ast_code_records WHERE complexity_score IS NOT NULL"
            )
            avg_complexity = cursor.fetchone()[0]
            stats['average_complexity'] = round(avg_complexity, 2) if avg_complexity else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}