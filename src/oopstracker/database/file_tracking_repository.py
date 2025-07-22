"""
Repository for file tracking operations.
Handles file change detection and tracking.
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Set, Optional

logger = logging.getLogger(__name__)


class FileTrackingRepository:
    """
    Repository for file tracking operations.
    """
    
    def __init__(self, connection_manager):
        """
        Initialize file tracking repository.
        
        Args:
            connection_manager: DatabaseConnectionManager instance
        """
        self.connection_manager = connection_manager
    
    def get_file_hash(self, file_path: str) -> Optional[str]:
        """
        Get stored file hash for a given file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File hash if exists, None otherwise
        """
        try:
            cursor = self.connection_manager.execute("""
                SELECT file_hash FROM ast_file_tracking 
                WHERE file_path = ?
            """, (file_path,))
            
            result = cursor.fetchone()
            return result['file_hash'] if result else None
            
        except Exception as e:
            logger.error(f"Failed to get file hash: {e}")
            return None
    
    def update_file_tracking(self, file_path: str, file_hash: str, unit_count: int = 0) -> bool:
        """
        Update file tracking information.
        
        Args:
            file_path: Path to the file
            file_hash: Hash of the file contents
            unit_count: Number of code units in the file
            
        Returns:
            True if updated successfully
        """
        try:
            # Get file modification time
            file_mtime = datetime.fromtimestamp(Path(file_path).stat().st_mtime).isoformat()
            scan_time = datetime.now().isoformat()
            
            self.connection_manager.execute("""
                INSERT OR REPLACE INTO ast_file_tracking 
                (file_path, file_hash, last_modified, last_scanned, unit_count)
                VALUES (?, ?, ?, ?, ?)
            """, (file_path, file_hash, file_mtime, scan_time, unit_count))
            
            self.connection_manager.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update file tracking: {e}")
            self.connection_manager.rollback()
            return False
    
    def get_changed_files(self, file_paths: List[str]) -> List[str]:
        """
        Get list of files that have changed since last scan.
        
        Args:
            file_paths: List of file paths to check
            
        Returns:
            List of changed file paths
        """
        changed_files = []
        
        for file_path in file_paths:
            if self._has_file_changed(file_path):
                changed_files.append(file_path)
        
        return changed_files
    
    def _has_file_changed(self, file_path: str) -> bool:
        """
        Check if a single file has changed.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file has changed or is new
        """
        try:
            # Calculate current file hash
            current_hash = self._calculate_file_hash(file_path)
            
            # Get stored hash
            stored_hash = self.get_file_hash(file_path)
            
            # If no stored hash or hash differs, file has changed
            return stored_hash is None or stored_hash != current_hash
            
        except Exception as e:
            logger.warning(f"Error checking file {file_path}: {e}")
            # Assume changed if we can't check
            return True
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA256 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hex string of file hash
        """
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def remove_file_tracking(self, file_path: str) -> bool:
        """
        Remove file tracking record.
        
        Args:
            file_path: File path to remove
            
        Returns:
            True if removed successfully
        """
        try:
            self.connection_manager.execute(
                "DELETE FROM ast_file_tracking WHERE file_path = ?",
                (file_path,)
            )
            self.connection_manager.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove file tracking: {e}")
            self.connection_manager.rollback()
            return False
    
    def get_tracked_files(self) -> Set[str]:
        """
        Get set of all tracked file paths.
        
        Returns:
            Set of file paths
        """
        try:
            cursor = self.connection_manager.execute(
                "SELECT file_path FROM ast_file_tracking"
            )
            return {row['file_path'] for row in cursor.fetchall()}
            
        except Exception as e:
            logger.error(f"Failed to get tracked files: {e}")
            return set()
    
    def check_deleted_files(self, current_files: Set[str]) -> List[str]:
        """
        Check which tracked files no longer exist.
        
        Args:
            current_files: Set of currently existing file paths
            
        Returns:
            List of deleted file paths
        """
        tracked_files = self.get_tracked_files()
        deleted_files = tracked_files - current_files
        
        if deleted_files:
            logger.info(f"Found {len(deleted_files)} deleted files")
            for file_path in deleted_files:
                logger.debug(f"  Deleted: {file_path}")
        
        return list(deleted_files)