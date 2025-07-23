"""
Path handling utilities for OOPStracker.
Centralized path processing with clean separation of concerns.
"""

from pathlib import Path
from typing import Union, Optional


class PathHandler:
    """Centralized path processing utility."""
    
    def __init__(self, project_root: Union[str, Path]):
        """Initialize with project root path.
        
        Args:
            project_root: Project root directory
        """
        self.project_root = Path(project_root).resolve()
    
    def normalize_path(self, path: Union[str, Path]) -> Path:
        """Convert any path input to normalized Path object.
        
        Args:
            path: Input path (string or Path)
            
        Returns:
            Normalized Path object
        """
        return Path(path).resolve()
    
    def get_relative_path(self, file_path: Path) -> Path:
        """Get relative path from project root.
        
        Args:
            file_path: File path to process
            
        Returns:
            Relative path from project root, or absolute path if outside project
        """
        if file_path.is_relative_to(self.project_root):
            return file_path.relative_to(self.project_root)
        return file_path
    
    def is_within_project(self, file_path: Path) -> bool:
        """Check if path is within project root.
        
        Args:
            file_path: File path to check
            
        Returns:
            True if path is within project root
        """
        return file_path.is_relative_to(self.project_root)