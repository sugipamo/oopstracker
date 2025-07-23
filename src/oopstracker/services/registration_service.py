"""
Registration service for code unit registration and management.
Handles file and code registration operations.
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path

from ..ast_analyzer import ASTAnalyzer, CodeUnit
from ..models import CodeRecord
from ..ast_database import ASTDatabaseManager
from ..simhash_detector import BKTree

logger = logging.getLogger(__name__)


class RegistrationService:
    """Service for handling code registration operations."""
    
    def __init__(self, analyzer: ASTAnalyzer, db_manager: ASTDatabaseManager, 
                 records: Dict[str, CodeRecord], code_units: Dict[str, CodeUnit], 
                 bk_tree: BKTree):
        """
        Initialize registration service.
        
        Args:
            analyzer: AST analyzer instance
            db_manager: Database manager instance
            records: Shared records dictionary
            code_units: Shared code units dictionary
            bk_tree: BK-tree instance for SimHash operations
        """
        self.analyzer = analyzer
        self.db_manager = db_manager
        self.records = records
        self.code_units = code_units
        self.bk_tree = bk_tree
    
    def register_file(self, file_path: str, force: bool = False) -> List[CodeRecord]:
        """
        Register all functions and classes from a Python file.
        
        Args:
            file_path: Path to Python file
            force: Force re-registration even if already registered
            
        Returns:
            List of registered CodeRecord objects
        """
        logger.info(f"Registering file: {file_path}")
        
        # Check if file has been modified since last registration
        if not force:
            existing_records = self.db_manager.get_file_records(file_path)
            if existing_records:
                file_mtime = Path(file_path).stat().st_mtime
                # Check if any record is newer than file
                if any(record.timestamp >= file_mtime for record in existing_records):
                    logger.info(f"File {file_path} already up to date")
                    return existing_records
        
        # Remove old records for this file
        self.db_manager.remove_file(file_path)
        
        # Also remove from memory
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
            record = self._register_unit(unit)
            if record:
                registered.append(record)
        
        logger.info(f"Registered {len(registered)} code units from {file_path}")
        return registered
    
    def register_code(self, source_code: str, function_name: Optional[str] = None,
                      file_path: Optional[str] = None) -> Optional[CodeRecord]:
        """
        Register a single piece of code.
        
        Args:
            source_code: Python source code
            function_name: Optional function/class name
            file_path: Optional file path
            
        Returns:
            CodeRecord if registered successfully
        """
        units = self.analyzer.extract_units_from_source(source_code)
        
        # If function_name specified, find that specific unit
        if function_name:
            for unit in units:
                if unit.name == function_name:
                    return self._register_unit(unit)
            logger.warning(f"Function '{function_name}' not found in source")
            return None
        
        # Otherwise register first unit
        if units:
            return self._register_unit(units[0])
        
        return None
    
    def _register_unit(self, unit: CodeUnit) -> Optional[CodeRecord]:
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
    
    def load_existing_data(self):
        """
        Load existing data from database into memory structures.
        Only loads records from files that currently exist.
        """
        try:
            # First, get list of all files in the database
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
                # Only load if file still exists
                if record.file_path and record.file_path in valid_files:
                    # Store in memory
                    self.records[record.code_hash] = record
                    self.code_units[record.code_hash] = unit
                    
                    # Rebuild BK-tree
                    if record.simhash is not None:
                        self.bk_tree.insert(record.simhash, record)
                    
                    loaded_count += 1
                else:
                    skipped_count += 1
            
            logger.info(f"Loaded {loaded_count} records from existing files, skipped {skipped_count} from deleted files")
            
        except Exception as e:
            logger.error(f"Failed to load existing data: {e}")