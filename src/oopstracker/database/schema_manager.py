"""
Database schema management.
Handles table creation, indexes, and schema versioning.
"""

import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)


class SchemaManager:
    """
    Manages database schema creation and migration.
    """
    
    SCHEMA_VERSION = "1.0"
    
    def __init__(self, connection_manager):
        """
        Initialize schema manager.
        
        Args:
            connection_manager: DatabaseConnectionManager instance
        """
        self.connection_manager = connection_manager
    
    def initialize_schema(self):
        """Create all database tables and indexes."""
        try:
            self._create_tables()
            self._create_indexes()
            self._initialize_metadata()
            logger.info("Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise
    
    def _create_tables(self):
        """Create all database tables."""
        tables = [
            self._get_code_records_table_sql(),
            self._get_dependencies_table_sql(),
            self._get_database_info_table_sql(),
            self._get_file_tracking_table_sql()
        ]
        
        for table_sql in tables:
            self.connection_manager.execute(table_sql)
    
    def _get_code_records_table_sql(self) -> str:
        """Get SQL for creating code records table."""
        return """
            CREATE TABLE IF NOT EXISTS ast_code_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_hash TEXT UNIQUE NOT NULL,
                code_content TEXT NOT NULL,
                function_name TEXT,
                file_path TEXT,
                timestamp TEXT NOT NULL,
                simhash TEXT,
                
                -- AST-specific fields
                unit_type TEXT NOT NULL,
                start_line INTEGER,
                end_line INTEGER,
                complexity_score INTEGER,
                ast_structure TEXT,
                
                -- Metadata as JSON
                metadata TEXT
            )
        """
    
    def _get_dependencies_table_sql(self) -> str:
        """Get SQL for creating dependencies table."""
        return """
            CREATE TABLE IF NOT EXISTS ast_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_hash TEXT NOT NULL,
                dependency TEXT NOT NULL,
                
                FOREIGN KEY (code_hash) REFERENCES ast_code_records (code_hash),
                UNIQUE(code_hash, dependency)
            )
        """
    
    def _get_database_info_table_sql(self) -> str:
        """Get SQL for creating database info table."""
        return """
            CREATE TABLE IF NOT EXISTS ast_database_info (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
    
    def _get_file_tracking_table_sql(self) -> str:
        """Get SQL for creating file tracking table."""
        return """
            CREATE TABLE IF NOT EXISTS ast_file_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT NOT NULL,
                last_modified TEXT NOT NULL,
                last_scanned TEXT NOT NULL,
                unit_count INTEGER DEFAULT 0
            )
        """
    
    def _create_indexes(self):
        """Create database indexes for performance."""
        indexes = [
            ("idx_code_hash", "ast_code_records", "code_hash"),
            ("idx_function_name", "ast_code_records", "function_name"),
            ("idx_file_path", "ast_code_records", "file_path"),
            ("idx_unit_type", "ast_code_records", "unit_type"),
            ("idx_simhash", "ast_code_records", "simhash"),
            ("idx_file_tracking_path", "ast_file_tracking", "file_path"),
            ("idx_file_tracking_hash", "ast_file_tracking", "file_hash")
        ]
        
        for index_name, table_name, column_name in indexes:
            sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})"
            self.connection_manager.execute(sql)
    
    def _initialize_metadata(self):
        """Initialize database metadata."""
        # Insert schema version
        self.connection_manager.execute("""
            INSERT OR REPLACE INTO ast_database_info (key, value)
            VALUES ('schema_version', ?)
        """, (self.SCHEMA_VERSION,))
        
        # Insert creation timestamp
        self.connection_manager.execute("""
            INSERT OR IGNORE INTO ast_database_info (key, value)
            VALUES ('created_at', ?)
        """, (datetime.now().isoformat(),))
        
        self.connection_manager.commit()
    
    def get_schema_version(self) -> str:
        """Get current schema version from database."""
        cursor = self.connection_manager.execute(
            "SELECT value FROM ast_database_info WHERE key = 'schema_version'"
        )
        result = cursor.fetchone()
        return result['value'] if result else None
    
    def needs_migration(self) -> bool:
        """Check if database needs schema migration."""
        current_version = self.get_schema_version()
        return current_version != self.SCHEMA_VERSION