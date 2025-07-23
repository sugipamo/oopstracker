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
            self._get_classification_rules_table_sql(),
            self._get_file_tracking_table_sql(),
            self._get_database_info_table_sql()
        ]
        
        for table_sql in tables:
            self.connection_manager.execute(table_sql)
    
    def _get_code_records_table_sql(self) -> str:
        """Get SQL for creating code records table."""
        return """
            CREATE TABLE IF NOT EXISTS code_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_hash TEXT UNIQUE NOT NULL,
                code_content TEXT NOT NULL,
                normalized_code TEXT,
                function_name TEXT,
                file_path TEXT,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                simhash TEXT
            )
        """
    
    def _get_classification_rules_table_sql(self) -> str:
        """Get SQL for creating classification rules table."""
        return """
            CREATE TABLE IF NOT EXISTS classification_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL,
                category TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                rule_type TEXT DEFAULT 'pattern',
                created_at TEXT NOT NULL
            )
        """
    
    def _get_database_info_table_sql(self) -> str:
        """Get SQL for creating database info table."""
        return """
            CREATE TABLE IF NOT EXISTS database_info (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
    
    def _get_file_tracking_table_sql(self) -> str:
        """Get SQL for creating file tracking table."""
        return """
            CREATE TABLE IF NOT EXISTS file_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                last_modified TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                scan_timestamp TEXT NOT NULL
            )
        """
    
    def _create_indexes(self):
        """Create database indexes for performance."""
        indexes = [
            ("idx_code_hash", "code_records", "code_hash"),
            ("idx_function_name", "code_records", "function_name"),
            ("idx_file_path", "code_records", "file_path"),
            ("idx_simhash", "code_records", "simhash"),
            ("idx_file_tracking_path", "file_tracking", "file_path"),
            ("idx_file_tracking_hash", "file_tracking", "file_hash"),
            ("idx_classification_rules_type", "classification_rules", "rule_type")
        ]
        
        for index_name, table_name, column_name in indexes:
            sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})"
            self.connection_manager.execute(sql)
    
    def _initialize_metadata(self):
        """Initialize database metadata."""
        # Insert schema version
        self.connection_manager.execute("""
            INSERT OR REPLACE INTO database_info (key, value)
            VALUES ('schema_version', ?)
        """, (self.SCHEMA_VERSION,))
        
        # Insert creation timestamp
        self.connection_manager.execute("""
            INSERT OR IGNORE INTO database_info (key, value)
            VALUES ('created_at', ?)
        """, (datetime.now().isoformat(),))
        
        self.connection_manager.commit()
    
    def get_schema_version(self) -> str:
        """Get current schema version from database."""
        cursor = self.connection_manager.execute(
            "SELECT value FROM database_info WHERE key = 'schema_version'"
        )
        result = cursor.fetchone()
        return result['value'] if result else None
    
    def needs_migration(self) -> bool:
        """Check if database needs schema migration."""
        current_version = self.get_schema_version()
        return current_version != self.SCHEMA_VERSION