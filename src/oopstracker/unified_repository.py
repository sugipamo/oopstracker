"""
Unified repository for all data operations without try-catch complexity.
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OperationResult:
    """Result of a repository operation."""
    success: bool
    data: Optional[Any] = None
    error_message: str = ""
    affected_rows: int = 0


class UnifiedRepository:
    """
    Centralized repository for all data operations.
    Eliminates try-catch complexity by using Result pattern.
    """
    
    def __init__(self, connection_manager):
        self.connection_manager = connection_manager
        self._setup_queries()
    
    def _setup_queries(self):
        """Pre-define all SQL queries."""
        self.queries = {
            'insert_code_record': """
                INSERT OR IGNORE INTO code_records 
                (code_hash, code_content, normalized_code, function_name, file_path, timestamp, metadata, simhash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            'select_code_record': """
                SELECT * FROM code_records WHERE code_hash = ?
            """,
            'select_all_records': """
                SELECT * FROM code_records ORDER BY timestamp DESC
            """,
            'insert_classification_rule': """
                INSERT OR REPLACE INTO classification_rules 
                (pattern, category, confidence, rule_type, created_at)
                VALUES (?, ?, ?, ?, ?)
            """,
            'select_classification_rules': """
                SELECT * FROM classification_rules WHERE rule_type = ?
            """,
            'insert_file_tracking': """
                INSERT OR REPLACE INTO file_tracking 
                (file_path, last_modified, file_hash, scan_timestamp)
                VALUES (?, ?, ?, ?)
            """,
            'select_changed_files': """
                SELECT file_path FROM file_tracking 
                WHERE last_modified > scan_timestamp OR file_hash != ?
            """
        }
    
    def create_code_record(self, record_data: Dict[str, Any]) -> OperationResult:
        """Create a code record."""
        connection = self.connection_manager.connection
        if not connection:
            return OperationResult(False, error_message="Database connection unavailable")
        cursor = connection.cursor()
        
        metadata = record_data.get('metadata', {})
        metadata_str = json.dumps(metadata) if isinstance(metadata, dict) else metadata or '{}'
        
        result = cursor.execute(
            self.queries['insert_code_record'],
            (
                record_data.get('code_hash'),
                record_data.get('code_content'),
                record_data.get('normalized_code'),
                record_data.get('function_name'),
                record_data.get('file_path'),
                record_data.get('timestamp', datetime.now()),
                metadata_str,
                record_data.get('simhash')
            )
        )
        
        success = result.rowcount > 0
        return OperationResult(
            success=success,
            affected_rows=result.rowcount,
            error_message="" if success else "Record already exists or insert failed"
        )
    
    def get_code_record(self, code_hash: str) -> OperationResult:
        """Get a code record by hash."""
        connection = self.connection_manager.connection
        if not connection:
            return OperationResult(False, error_message="Database connection unavailable")
        cursor = connection.cursor()
        
        result = cursor.execute(self.queries['select_code_record'], (code_hash,))
        record = result.fetchone()
        
        if record:
            return OperationResult(True, data=dict(record))
        else:
            return OperationResult(False, error_message="Record not found")
    
    def get_all_code_records(self) -> OperationResult:
        """Get all code records."""
        connection = self.connection_manager.connection
        if not connection:
            return OperationResult(False, error_message="Database connection unavailable")
        cursor = connection.cursor()
        
        result = cursor.execute(self.queries['select_all_records'])
        records = [dict(row) for row in result.fetchall()]
        
        return OperationResult(True, data=records, affected_rows=len(records))
    
    def create_classification_rule(self, rule_data: Dict[str, Any]) -> OperationResult:
        """Create a classification rule."""
        connection = self.connection_manager.connection
        if not connection:
            return OperationResult(False, error_message="Database connection unavailable")
        cursor = connection.cursor()
        
        result = cursor.execute(
            self.queries['insert_classification_rule'],
            (
                rule_data.get('pattern'),
                rule_data.get('category'),
                rule_data.get('confidence', 0.5),
                rule_data.get('rule_type', 'pattern'),
                datetime.now()
            )
        )
        
        return OperationResult(True, affected_rows=result.rowcount)
    
    def get_classification_rules(self, rule_type: str = 'pattern') -> OperationResult:
        """Get classification rules by type."""
        connection = self.connection_manager.connection
        if not connection:
            return OperationResult(False, error_message="Database connection unavailable")
        cursor = connection.cursor()
        
        result = cursor.execute(self.queries['select_classification_rules'], (rule_type,))
        rules = [dict(row) for row in result.fetchall()]
        
        return OperationResult(True, data=rules, affected_rows=len(rules))
    
    def track_file(self, file_data: Dict[str, Any]) -> OperationResult:
        """Track file changes."""
        connection = self.connection_manager.connection
        if not connection:
            return OperationResult(False, error_message="Database connection unavailable")
        cursor = connection.cursor()
        
        result = cursor.execute(
            self.queries['insert_file_tracking'],
            (
                file_data.get('file_path'),
                file_data.get('last_modified'),
                file_data.get('file_hash'),
                datetime.now()
            )
        )
        
        return OperationResult(True, affected_rows=result.rowcount)
    
    def get_changed_files(self, reference_hash: str) -> OperationResult:
        """Get files that have changed."""
        connection = self.connection_manager.connection
        if not connection:
            return OperationResult(False, error_message="Database connection unavailable")
        cursor = connection.cursor()
        
        result = cursor.execute(self.queries['select_changed_files'], (reference_hash,))
        files = [row[0] for row in result.fetchall()]
        
        return OperationResult(True, data=files, affected_rows=len(files))
    
    def bulk_insert_records(self, records_data: List[Dict[str, Any]]) -> OperationResult:
        """Bulk insert multiple records efficiently."""
        connection = self.connection_manager.connection
        if not connection:
            return OperationResult(False, error_message="Database connection unavailable")
        cursor = connection.cursor()
        
        insert_data = [
            (
                record.get('code_hash'),
                record.get('code_content'),
                record.get('normalized_code'),
                record.get('function_name'),
                record.get('file_path'),
                record.get('timestamp', datetime.now()),
                json.dumps(record.get('metadata', {})) if isinstance(record.get('metadata'), dict) else record.get('metadata', '{}'),
                record.get('simhash')
            )
            for record in records_data
        ]
        
        cursor.executemany(self.queries['insert_code_record'], insert_data)
        
        return OperationResult(True, affected_rows=len(insert_data))
    
    def execute_custom_query(self, query: str, params: Tuple = ()) -> OperationResult:
        """Execute custom query with parameters."""
        connection = self.connection_manager.connection
        if not connection:
            return OperationResult(False, error_message="Database connection unavailable")
        cursor = connection.cursor()
        
        result = cursor.execute(query, params)
        
        if query.strip().upper().startswith('SELECT'):
            data = [dict(row) for row in result.fetchall()]
            return OperationResult(True, data=data, affected_rows=len(data))
        else:
            return OperationResult(True, affected_rows=result.rowcount)
    
    def get_statistics(self) -> OperationResult:
        """Get database statistics."""
        stats_queries = {
            'total_records': 'SELECT COUNT(*) as count FROM code_records',
            'total_files': 'SELECT COUNT(DISTINCT file_path) as count FROM code_records',
            'total_functions': 'SELECT COUNT(*) as count FROM code_records WHERE function_name IS NOT NULL'
        }
        
        connection = self.connection_manager.connection
        if not connection:
            return OperationResult(False, error_message="Database connection unavailable")
        cursor = connection.cursor()
        
        stats = {}
        for stat_name, query in stats_queries.items():
            result = cursor.execute(query)
            row = result.fetchone()
            stats[stat_name] = row[0] if row else 0
        
        return OperationResult(True, data=stats)