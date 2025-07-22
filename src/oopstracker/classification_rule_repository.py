"""
Repository for managing classification rules in SQLite.
Extracted from ai_analysis_coordinator.py to improve separation of concerns.
"""

import logging
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List

from .ai_analysis_models import ClassificationRule


class ClassificationRuleRepository:
    """Repository for managing classification rules in SQLite."""
    
    def __init__(self, db_path: str = "classification_rules.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize the database schema."""
        try:
            # Ensure directory exists
            db_dir = Path(self.db_path).parent
            if db_dir != Path('.'):
                db_dir.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS classification_rules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pattern TEXT NOT NULL,
                        category TEXT NOT NULL,
                        reasoning TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        success_count INTEGER DEFAULT 0,
                        failure_count INTEGER DEFAULT 0
                    )
                ''')
                conn.commit()
                
                # Add default rules if table is empty
                cursor = conn.execute("SELECT COUNT(*) FROM classification_rules")
                if cursor.fetchone()[0] == 0:
                    self._add_default_rules(conn)
                    
        except sqlite3.Error as e:
            self.logger.error(f"Failed to initialize classification rules database: {e}")
            raise RuntimeError(f"Cannot initialize database at {self.db_path}: {e}")
    
    def _add_default_rules(self, conn: sqlite3.Connection):
        """Add default classification rules for common patterns."""
        default_rules = [
            # Test functions
            ClassificationRule(
                pattern=r"def\s+test_\w+|def\s+\w+_test",
                category="test",
                reasoning="Test function pattern",
                created_at=datetime.now()
            ),
            # Getter/Setter
            ClassificationRule(
                pattern=r"def\s+(get|set)_\w+|def\s+(get|set)[A-Z]\w*",
                category="getter_setter",
                reasoning="Getter/setter method pattern",
                created_at=datetime.now()
            ),
            # Main entry points
            ClassificationRule(
                pattern=r"def\s+main\s*\(|if\s+__name__\s*==\s*['\"]__main__['\"]",
                category="utility",
                reasoning="Main entry point pattern",
                created_at=datetime.now()
            ),
            # Initialization
            ClassificationRule(
                pattern=r"def\s+__init__\s*\(",
                category="constructor",
                reasoning="Class constructor pattern",
                created_at=datetime.now()
            ),
            # API endpoints
            ClassificationRule(
                pattern=r"@(app|router)\.(get|post|put|delete|patch)",
                category="web_api",
                reasoning="Web API endpoint pattern",
                created_at=datetime.now()
            ),
            # Data processing
            ClassificationRule(
                pattern=r"def\s+(parse|process|transform|convert|extract)_\w+",
                category="data_processing",
                reasoning="Data processing function pattern",
                created_at=datetime.now()
            ),
            # Business logic
            ClassificationRule(
                pattern=r"def\s+(calculate|compute|validate|check|verify)_\w+",
                category="business_logic",
                reasoning="Business logic function pattern",
                created_at=datetime.now()
            ),
            # Simple utility
            ClassificationRule(
                pattern=r"def\s+\w+\s*\(\s*\)\s*:\s*(pass|\.\.\.|\n\s+return)",
                category="utility",
                reasoning="Simple utility function pattern",
                created_at=datetime.now()
            ),
        ]
        
        for rule in default_rules:
            try:
                conn.execute('''
                    INSERT INTO classification_rules (pattern, category, reasoning, created_at, success_count, failure_count)
                    VALUES (?, ?, ?, ?, 0, 0)
                ''', (rule.pattern, rule.category, rule.reasoning, rule.created_at.isoformat()))
            except sqlite3.Error:
                # Ignore duplicates
                pass
        
        conn.commit()
        self.logger.info(f"Added {len(default_rules)} default classification rules")
    
    def save_rule(self, rule: ClassificationRule) -> int:
        """Save a classification rule to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    INSERT INTO classification_rules (pattern, category, reasoning, created_at, success_count, failure_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (rule.pattern, rule.category, rule.reasoning, rule.created_at.isoformat(), 
                      rule.success_count, rule.failure_count))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            self.logger.error(f"Failed to save classification rule: {e}")
            raise RuntimeError(f"Cannot save rule to database: {e}")
    
    def get_rules_for_category(self, category: str) -> List[ClassificationRule]:
        """Get all rules for a specific category, ordered by success rate."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT pattern, category, reasoning, created_at, success_count, failure_count
                    FROM classification_rules
                    WHERE category = ?
                    ORDER BY (success_count * 1.0 / (success_count + failure_count + 1)) DESC,
                             success_count DESC, created_at DESC
                ''', (category,))
                
                rules = []
                for row in cursor.fetchall():
                    try:
                        rules.append(ClassificationRule(
                            pattern=row[0],
                            category=row[1],
                            reasoning=row[2],
                            created_at=datetime.fromisoformat(row[3]),
                            success_count=row[4],
                            failure_count=row[5]
                        ))
                    except Exception as e:
                        self.logger.warning(f"Skipping invalid rule record: {e}")
                        continue
                return rules
        except sqlite3.Error as e:
            self.logger.error(f"Failed to retrieve rules: {e}")
            return []
    
    def get_all_rules(self) -> List[ClassificationRule]:
        """Get all classification rules."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT pattern, category, reasoning, created_at, success_count, failure_count
                    FROM classification_rules
                    ORDER BY success_count DESC, created_at DESC
                ''')
                
                rules = []
                for row in cursor.fetchall():
                    try:
                        rules.append(ClassificationRule(
                            pattern=row[0],
                            category=row[1],
                            reasoning=row[2],
                            created_at=datetime.fromisoformat(row[3]),
                            success_count=row[4],
                            failure_count=row[5]
                        ))
                    except Exception as e:
                        self.logger.warning(f"Skipping invalid rule record: {e}")
                        continue
                return rules
        except sqlite3.Error as e:
            self.logger.error(f"Failed to retrieve all rules: {e}")
            return []
    
    def update_rule_stats(self, pattern: str, category: str, success: bool):
        """Update success/failure statistics for a rule."""
        try:
            field = "success_count" if success else "failure_count"
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f'''
                    UPDATE classification_rules
                    SET {field} = {field} + 1
                    WHERE pattern = ? AND category = ?
                ''', (pattern, category))
                conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Failed to update rule stats: {e}")