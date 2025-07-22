"""
File scanning service for OOPStracker.
Handles file discovery, filtering, and scanning operations.
"""

import logging
from pathlib import Path
from typing import List, Set, Optional, Tuple
import asyncio

from ..models import CodeRecord
from ..ignore_patterns import IgnorePatterns
from ..progress_reporter import ProgressReporter
from ..exceptions import OOPSTrackerError


class FileScanService:
    """Service for scanning and analyzing files."""
    
    def __init__(self, detector, logger: Optional[logging.Logger] = None):
        """Initialize the file scan service.
        
        Args:
            detector: The AST SimHash detector instance
            logger: Optional logger instance
        """
        self.detector = detector
        self.logger = logger or logging.getLogger(__name__)
        
    def find_files(self, path: str, pattern: str = "*.py", 
                   exclude_dirs: Optional[List[str]] = None) -> List[Path]:
        """Find all files matching the pattern in the given path.
        
        Args:
            path: Directory or file path to scan
            pattern: File pattern to match (default: *.py)
            exclude_dirs: List of directory names to exclude
            
        Returns:
            List of Path objects for matching files
        """
        path_obj = Path(path)
        
        if path_obj.is_file():
            # Single file specified
            return [path_obj] if path_obj.match(pattern) else []
            
        if not path_obj.is_dir():
            raise OOPSTrackerError(f"Path not found: {path}")
            
        # Initialize ignore patterns
        ignore_patterns = IgnorePatterns(str(path_obj))
        
        # Find all matching files
        all_files = []
        for file_path in path_obj.rglob(pattern):
            if ignore_patterns.should_ignore(str(file_path)):
                continue
            all_files.append(file_path)
            
        # Sort files for consistent ordering
        all_files.sort()
        
        self.logger.info(f"Found {len(all_files)} {pattern} files in {path}")
        return all_files
        
    def get_changed_files(self, all_files: List[Path]) -> List[Path]:
        """Get files that have changed since last scan.
        
        Args:
            all_files: List of all files to check
            
        Returns:
            List of changed files
        """
        if not hasattr(self.detector, 'db_manager'):
            # No DB manager, all files are "new"
            return all_files
            
        changed_files = self.detector.db_manager.get_changed_files(all_files)
        self.logger.info(f"Found {len(changed_files)} changed files")
        return changed_files
        
    async def scan_files(self, files_to_scan: List[Path], 
                        force: bool = False,
                        progress_reporter: Optional[ProgressReporter] = None) -> Tuple[List[CodeRecord], int]:
        """Scan files and register code units.
        
        Args:
            files_to_scan: List of files to scan
            force: Force re-scanning of all files
            progress_reporter: Optional progress reporter
            
        Returns:
            Tuple of (new_records, updated_files_count)
        """
        new_records = []
        updated_files = 0
        
        # Show progress if there are many files
        if len(files_to_scan) > 10:
            self.logger.info(f"Scanning {len(files_to_scan)} files...")
            
        for i, file_path in enumerate(files_to_scan):
            # Show progress for large scans
            if progress_reporter:
                progress_reporter.print_progress(i + 1, len(files_to_scan), unit="files")
                
            try:
                records = self.detector.register_file(str(file_path), force=force)
                if records:
                    new_records.extend(records)
                    updated_files += 1
            except Exception as e:
                self.logger.warning(f"Failed to scan {file_path}: {e}")
                
        return new_records, updated_files
        
    def find_duplicates_in_records(self, records: List[CodeRecord], 
                                  file_path: Optional[str] = None) -> List[dict]:
        """Find duplicates in newly registered records.
        
        Args:
            records: List of code records to check
            file_path: Optional file path for context
            
        Returns:
            List of duplicate information dictionaries
        """
        duplicates_found = []
        
        for record in records:
            # Skip module-level records
            if record.metadata and record.metadata.get('type') == 'module':
                continue
                
            result = self.detector.find_similar(
                record.code_content, 
                record.function_name, 
                file_path
            )
            
            if result.is_duplicate and result.matched_records:
                # Collect duplicate info for summary
                dup_info = {
                    'type': record.metadata.get('type', 'unknown') if record.metadata else 'unknown',
                    'name': record.function_name,
                    'file': file_path or record.file_path,
                    'matches': []
                }
                
                for matched in result.matched_records[:3]:
                    # Skip if it's the same record we just added
                    if matched.code_hash == record.code_hash:
                        continue
                        
                    dup_info['matches'].append({
                        'name': matched.function_name or 'N/A',
                        'file': matched.file_path or 'N/A',
                        'similarity': matched.similarity_score or 0
                    })
                
                if dup_info['matches']:
                    duplicates_found.append(dup_info)
                    
        return duplicates_found