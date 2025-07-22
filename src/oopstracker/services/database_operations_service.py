"""
Database Operations Service - Extracted common database operations.
Implements the Extract pattern to centralize database operations.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Union

from ..models import CodeRecord
from ..exceptions import DatabaseError


class DatabaseOperationsService:
    """
    Centralized service for database operations.
    
    This service extracts common database operations that were scattered 
    across core.py, ast_database.py, and other database-related modules.
    """
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        self._ensure_directory()
    
    def _ensure_directory(self):
        """Ensure the database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper configuration."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Enable column access by name
            return conn
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to connect to database: {e}")
    
    def execute_safe(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a query safely with error handling.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Cursor object
            
        Raises:
            DatabaseError: If query execution fails
        """
        try:
            with self.get_connection() as conn:
                return conn.execute(query, params)
        except sqlite3.Error as e:
            self.logger.error(f"Database query failed: {query}, params: {params}, error: {e}")
            raise DatabaseError(f"Query execution failed: {e}")
    
    def execute_many_safe(self, query: str, params_list: List[tuple]) -> None:
        """
        Execute multiple queries safely with error handling.
        
        Args:
            query: SQL query to execute
            params_list: List of parameter tuples
            
        Raises:
            DatabaseError: If query execution fails
        """
        try:
            with self.get_connection() as conn:
                conn.executemany(query, params_list)
        except sqlite3.Error as e:
            self.logger.error(f"Database batch query failed: {query}, error: {e}")
            raise DatabaseError(f"Batch query execution failed: {e}")
    
    def create_table_safe(self, table_name: str, columns: Dict[str, str]) -> None:
        """
        Create a table safely with proper error handling.
        
        Args:
            table_name: Name of the table to create
            columns: Dictionary of column_name -> column_definition
            
        Raises:
            DatabaseError: If table creation fails
        """
        columns_def = ', '.join([f"{name} {definition}" for name, definition in columns.items()])
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_def})"
        
        try:
            with self.get_connection() as conn:
                conn.execute(query)
                self.logger.debug(f"Created/verified table: {table_name}")
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to create table {table_name}: {e}")
    
    def add_column_safe(self, table_name: str, column_name: str, column_def: str) -> bool:
        """
        Add a column to existing table safely.
        
        Args:
            table_name: Name of the table
            column_name: Name of the new column
            column_def: Column definition
            
        Returns:
            True if column was added, False if it already existed
            
        Raises:
            DatabaseError: If column addition fails for reasons other than existing column
        """
        query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
        
        try:
            with self.get_connection() as conn:
                conn.execute(query)
                self.logger.debug(f"Added column {column_name} to {table_name}")
                return True
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                self.logger.debug(f"Column {column_name} already exists in {table_name}")
                return False
            else:
                raise DatabaseError(f"Failed to add column {column_name} to {table_name}: {e}")
    
    def serialize_metadata(self, metadata: Optional[Dict[str, Any]]) -> Optional[str]:
        """Serialize metadata dictionary to JSON string."""
        if metadata is None:
            return None
        try:
            return json.dumps(metadata)
        except (TypeError, ValueError) as e:
            self.logger.warning(f"Failed to serialize metadata: {e}")
            return None
    
    def deserialize_metadata(self, metadata_str: Optional[str]) -> Optional[Dict[str, Any]]:
        """Deserialize JSON string to metadata dictionary."""
        if not metadata_str:
            return None
        try:
            return json.loads(metadata_str)
        except (json.JSONDecodeError, TypeError) as e:
            self.logger.warning(f"Failed to deserialize metadata: {e}")
            return None
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get information about table structure.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        try:
            cursor = self.execute_safe(f"PRAGMA table_info({table_name})")
            return [dict(row) for row in cursor.fetchall()]
        except DatabaseError:
            return []
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        try:
            cursor = self.execute_safe(query, (table_name,))
            return cursor.fetchone() is not None
        except DatabaseError:
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get basic statistics about the database."""
        stats = {
            "db_path": str(self.db_path),
            "db_exists": self.db_path.exists(),
            "db_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
            "tables": []
        }
        
        try:
            cursor = self.execute_safe("SELECT name FROM sqlite_master WHERE type='table'")
            table_names = [row[0] for row in cursor.fetchall()]
            
            for table_name in table_names:
                try:
                    cursor = self.execute_safe(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    stats["tables"].append({"name": table_name, "row_count": count})
                except DatabaseError:
                    stats["tables"].append({"name": table_name, "row_count": "error"})
                    
        except DatabaseError:
            stats["error"] = "Could not read database tables"
        
        return stats