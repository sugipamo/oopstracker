"""
Data management layer for AST SimHash detector.
Handles record registration, storage, and retrieval.
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path

from ..ast_analyzer import ASTAnalyzer, CodeUnit
from ..models import CodeRecord
from ..simhash_detector import BKTree
from ..ast_database import ASTDatabaseManager

logger = logging.getLogger(__name__)


class DataManagementLayer:
    """Manages data persistence and memory structures."""
    
    def __init__(self, db_path: str = "oopstracker_ast.db"):
        """Initialize data management layer."""
        self.db_manager = ASTDatabaseManager(db_path)
        self.analyzer = ASTAnalyzer()
        self.bk_tree = BKTree()
        self.code_units: Dict[str, CodeUnit] = {}
        self.records: Dict[str, CodeRecord] = {}
        
    def load_existing_data(self) -> tuple[int, int]:
        """
        Load existing data from database into memory structures.
        Returns (loaded_count, skipped_count).
        """
        try:
            existing_files = self.db_manager.get_existing_files()
            
            # Filter to only files that still exist
            valid_files = set()
            for file_path in existing_files:
                if Path(file_path).exists():
                    valid_files.add(file_path)
            
            logger.info(f"Found {len(valid_files)} existing files out of {len(existing_files)} tracked files")
            
            # Load all records
            existing_data = self.db_manager.get_all_records()
            loaded_count = 0
            skipped_count = 0
            
            for record, unit in existing_data:
                if record.file_path and record.file_path in valid_files:
                    self.records[record.code_hash] = record
                    self.code_units[record.code_hash] = unit
                    
                    if record.simhash is not None:
                        self.bk_tree.insert(record.simhash, record)
                    
                    loaded_count += 1
                else:
                    skipped_count += 1
            
            logger.info(f"Loaded {loaded_count} records, skipped {skipped_count}")
            return loaded_count, skipped_count
            
        except Exception as e:
            logger.error(f"Failed to load existing data: {e}")
            return 0, 0
    
    def register_file(self, file_path: str, force: bool = False) -> List[CodeRecord]:
        """Register all functions and classes from a Python file."""
        logger.info(f"Registering file: {file_path}")
        
        # Check if file has been modified since last registration
        if not force:
            existing_records = self.db_manager.get_file_records(file_path)
            if existing_records:
                file_mtime = Path(file_path).stat().st_mtime
                if any(record.timestamp >= file_mtime for record in existing_records):
                    logger.info(f"File {file_path} already up to date")
                    return existing_records
        
        # Remove old records for this file
        self.db_manager.remove_file(file_path)
        
        # Remove from memory
        to_remove = [hash for hash, record in self.records.items() 
                     if record.file_path == file_path]
        for hash in to_remove:
            self.records.pop(hash, None)
            self.code_units.pop(hash, None)
        
        # Extract and register code units
        units = self.analyzer.extract_code_units(file_path)
        
        if not units:
            logger.warning(f"No code units found in {file_path}")
            return []
        
        registered = []
        for unit in units:
            record = self.register_unit(unit)
            if record:
                registered.append(record)
        
        logger.info(f"Registered {len(registered)} code units from {file_path}")
        return registered
    
    def register_unit(self, unit: CodeUnit) -> Optional[CodeRecord]:
        """Register a single code unit."""
        # Check if this exact code already exists
        existing_record = self.records.get(unit.code_hash)
        if existing_record:
            logger.debug(f"Code unit already registered: {unit.name}")
            return existing_record
        
        # Calculate SimHash
        simhash = self.analyzer.calculate_simhash(unit)
        
        # Create record
        record = CodeRecord(
            code_hash=unit.code_hash,
            function_name=unit.name,
            file_path=unit.file_path,
            start_line=unit.start_line,
            end_line=unit.end_line,
            code_type=unit.unit_type,
            simhash=simhash,
            ast_hash=unit.ast_hash,
            semantic_hash=unit.semantic_hash,
            intent_category=unit.intent_category,
            code_snippet=unit.source[:200] + "..." if len(unit.source) > 200 else unit.source
        )
        
        # Store in memory
        self.records[record.code_hash] = record
        self.code_units[record.code_hash] = unit
        
        # Add to BK-tree
        if simhash is not None:
            self.bk_tree.insert(simhash, record)
        
        # Persist to database
        try:
            self.db_manager.add_record(record, unit)
        except Exception as e:
            logger.error(f"Failed to persist record: {e}")
        
        return record
    
    def register_code(self, source_code: str, function_name: Optional[str] = None,
                      file_path: Optional[str] = None) -> Optional[CodeRecord]:
        """Register a single piece of code."""
        units = self.analyzer.extract_units_from_source(source_code)
        
        # If function_name specified, find that specific unit
        if function_name:
            for unit in units:
                if unit.name == function_name:
                    return self.register_unit(unit)
            logger.warning(f"Function '{function_name}' not found in source")
            return None
        
        # Otherwise register first unit
        if units:
            return self.register_unit(units[0])
        
        return None
    
    def get_all_records(self) -> List[CodeRecord]:
        """Get all registered records."""
        return list(self.records.values())
    
    def get_record(self, code_hash: str) -> Optional[CodeRecord]:
        """Get a specific record by hash."""
        return self.records.get(code_hash)
    
    def get_unit(self, code_hash: str) -> Optional[CodeUnit]:
        """Get a specific code unit by hash."""
        return self.code_units.get(code_hash)
    
    def clear_all(self):
        """Clear all stored data."""
        self.db_manager.clear_all()
        self.bk_tree = BKTree()
        self.code_units.clear()
        self.records.clear()
        logger.info("Cleared all data")