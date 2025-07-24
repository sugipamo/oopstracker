"""
Database connection management.
Handles SQLite connection lifecycle and configuration.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """
    Manages database connections with proper lifecycle management.
    """
    
    def __init__(self, db_path: str = "oopstracker_ast.db"):
        """
        Initialize connection manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._connection: Optional[sqlite3.Connection] = None
    
    @property
    def connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = self._create_connection()
        return self._connection
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create and configure a new database connection."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Enable column access by name
            
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Optimize for performance
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            
            # Set busy timeout to 5 seconds to handle concurrent access
            conn.execute("PRAGMA busy_timeout = 5000")
            
            logger.info(f"Created database connection: {self.db_path}")
            return conn
            
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            raise
    
    def execute(self, query: str, params: Optional[tuple] = None) -> sqlite3.Cursor:
        """
        Execute a database query.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Cursor with query results
        """
        cursor = self.connection.cursor()
        if params:
            return cursor.execute(query, params)
        return cursor.execute(query)
    
    def commit(self):
        """Commit current transaction."""
        if self._connection:
            self._connection.commit()
    
    def rollback(self):
        """Rollback current transaction."""
        if self._connection:
            self._connection.rollback()
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.
        
        Automatically commits on success, rolls back on error.
        """
        try:
            yield self
            self.commit()
        except Exception:
            self.rollback()
            raise
    
    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.debug("Database connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()