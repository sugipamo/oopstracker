"""
Ignore patterns for OOPStracker.
Handles .oopsignore files and default exclusion patterns.
"""

import fnmatch
import os
import logging
from pathlib import Path
from typing import List, Set, Optional

from .path_handler import PathHandler

logger = logging.getLogger(__name__)


class IgnorePatterns:
    """Manages ignore patterns for OOPStracker scanning."""
    
    # Default patterns to exclude (system libraries, virtual environments, etc.)
    DEFAULT_PATTERNS = [
        # Virtual environments
        ".venv/",
        "venv/",
        "env/",
        ".env/",
        "ENV/",
        "env.bak/",
        "venv.bak/",
        
        # Python cache and bytecode
        "__pycache__/",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        "*.so",
        "*.egg-info/",
        "*.dist-info/",
        
        # Build and distribution
        "build/",
        "dist/",
        ".tox/",
        ".pytest_cache/",
        ".coverage",
        "htmlcov/",
        ".mypy_cache/",
        ".ruff_cache/",
        
        # Package management
        "site-packages/",
        
        # Python initialization files
        "__init__.py",
        "*/site-packages/*",
        ".local/lib/python*/site-packages/",
        "lib/python*/site-packages/",
        "node_modules/",
        "bower_components/",
        
        # Version control
        ".git/",
        ".gitignore",
        ".gitmodules",
        ".svn/",
        ".hg/",
        ".bzr/",
        
        # IDE and editors
        ".vscode/",
        ".idea/",
        "*.swp",
        "*.swo",
        "*.tmp",
        "*~",
        ".DS_Store",
        "Thumbs.db",
        
        # Logs and databases
        "*.log",
        "*.db",
        "*.sqlite",
        "*.sqlite3",
        
        # Configuration files (potentially sensitive)
        ".env",
        ".env.*",
        "config.local.*",
        "secrets.*",
        
        # Documentation generation
        "docs/_build/",
        "docs/build/",
        "_build/",
        ".sphinx/",
        
        # System directories (Unix/Linux)
        "/usr/lib/python*/",
        "/usr/local/lib/python*/",
        "/opt/python*/",
        "/Library/Python/*/",
        
        # Conda environments
        ".conda/",
        "miniconda*/",
        "anaconda*/",
        "envs/",
        
        # Testing
        ".pytest_cache/",
        ".coverage",
        "htmlcov/",
        ".tox/",
        
        # Common temporary directories
        "tmp/",
        "temp/",
        ".tmp/",
        ".temp/",
    ]
    
    def __init__(self, ignore_file: Optional[str] = None, project_root: Optional[str] = None, 
                 use_gitignore: bool = True, include_tests: bool = False):
        """
        Initialize ignore patterns.
        
        Args:
            ignore_file: Path to .oopsignore file (default: .oopsignore)
            project_root: Project root directory (default: current directory)
            use_gitignore: Whether to respect .gitignore files (default: True)
            include_tests: Whether to include test directories and test functions (default: False)
        """
        self.path_handler = PathHandler(project_root or os.getcwd())
        self.ignore_file = ignore_file or ".oopsignore"
        self.use_gitignore = use_gitignore
        self.include_tests = include_tests
        self.patterns: Set[str] = set()
        self.gitignore_patterns: Set[str] = set()
        
        # Load default patterns
        self.patterns.update(self.DEFAULT_PATTERNS)
        
        # Load .gitignore patterns
        if self.use_gitignore:
            self.load_gitignore_files()
        
        # Load custom patterns from ignore file
        self.load_ignore_file()
    
    def load_ignore_file(self) -> None:
        """Load patterns from .oopsignore file."""
        ignore_path = self.path_handler.project_root / self.ignore_file
        
        if not ignore_path.exists():
            return
        
        try:
            with open(ignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        self.patterns.add(line)
        except Exception as e:
            print(f"⚠️  Warning: Could not read {ignore_path}: {e}")
    
    def load_gitignore_files(self) -> None:
        """Load patterns from .gitignore files (project root and parent directories)."""
        # Start from project root and walk up to find .gitignore files
        current_dir = self.path_handler.project_root
        
        while current_dir != current_dir.parent:  # Stop at filesystem root
            gitignore_path = current_dir / ".gitignore"
            
            if gitignore_path.exists():
                try:
                    with open(gitignore_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            # Skip empty lines and comments
                            if line and not line.startswith('#'):
                                # Convert gitignore patterns to our format
                                pattern = self._convert_gitignore_pattern(line, current_dir)
                                if pattern:
                                    self.gitignore_patterns.add(pattern)
                    
                    logger.debug(f"Loaded .gitignore from {gitignore_path}")
                except Exception as e:
                    logger.warning(f"Could not read {gitignore_path}: {e}")
            
            current_dir = current_dir.parent
        
        if self.gitignore_patterns:
            logger.info(f"Loaded {len(self.gitignore_patterns)} .gitignore patterns")
    
    def _convert_gitignore_pattern(self, pattern: str, gitignore_dir: Path) -> Optional[str]:
        """
        Convert a .gitignore pattern to our internal format.
        
        Args:
            pattern: Raw pattern from .gitignore
            gitignore_dir: Directory containing the .gitignore file
            
        Returns:
            Converted pattern or None if should be skipped
        """
        # Skip negation patterns for now (these are complex to handle correctly)
        if pattern.startswith('!'):
            return None
        
        # Remember if this is a directory pattern
        is_directory = pattern.endswith('/')
        
        # Calculate relative path from project root to gitignore directory
        if self.path_handler.is_within_project(gitignore_dir):
            rel_gitignore_dir = self.path_handler.get_relative_path(gitignore_dir)
            if str(rel_gitignore_dir) != '.':
                # Prefix pattern with relative directory path
                if is_directory:
                    pattern = str(rel_gitignore_dir / pattern[:-1]) + '/'
                else:
                    pattern = str(rel_gitignore_dir / pattern)
        else:
            # gitignore_dir is outside project root, skip
            return None
        
        return pattern
    
    def _is_test_file(self, file_path: Path, path_str: str) -> bool:
        """Check if a file is a test file that should be excluded by default."""
        # Check if in test directories
        test_dirs = ['test', 'tests', 'testing', '__test__', '__tests__']
        path_parts = Path(path_str).parts
        
        # Check if any part of the path is a test directory
        if any(part.lower() in test_dirs for part in path_parts):
            return True
        
        # Check if filename starts with 'test_' or ends with '_test.py'
        filename = file_path.name.lower()
        if filename.startswith('test_') or filename.endswith('_test.py'):
            return True
        
        # Check if filename contains 'test' and is a Python file
        if 'test' in filename and filename.endswith('.py'):
            return True
        
        return False
    
    def _matches_gitignore_patterns(self, path_str: str, path_parts: tuple) -> bool:
        """Check if path matches any .gitignore patterns."""
        for pattern in self.gitignore_patterns:
            # Directory patterns
            if pattern.endswith('/'):
                dir_pattern = pattern.rstrip('/')
                # Check if the path starts with the directory pattern
                if path_str.startswith(dir_pattern + '/') or path_str == dir_pattern:
                    return True
                # Also check with wildcard matching
                if fnmatch.fnmatch(path_str, dir_pattern + '/*'):
                    return True
            
            # File patterns
            else:
                # Exact match
                if fnmatch.fnmatch(path_str, pattern):
                    return True
                
                # For patterns without path separators, match against individual parts
                if '/' not in pattern:
                    if any(fnmatch.fnmatch(part, pattern) for part in path_parts):
                        return True
                
                # Wildcard patterns
                if '*' in pattern or '?' in pattern:
                    if fnmatch.fnmatch(path_str, pattern):
                        return True
        
        return False
    
    def should_ignore(self, file_path: Path) -> bool:
        """
        Check if a file should be ignored.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file should be ignored, False otherwise
        """
        # Normalize input and get relative path for matching
        normalized_path = self.path_handler.normalize_path(file_path)
        rel_path = self.path_handler.get_relative_path(normalized_path)
        
        path_str = str(rel_path)
        path_parts = rel_path.parts
        
        # Check test exclusion first (if tests not included)
        if not self.include_tests and self._is_test_file(file_path, path_str):
            return True
        
        # Check gitignore patterns first
        if self._matches_gitignore_patterns(path_str, path_parts):
            return True
        
        # Check default and custom patterns
        for pattern in self.patterns:
            # Handle negation patterns (starting with !)
            if pattern.startswith('!'):
                # This is a whitelist pattern, handle separately
                continue
            
            # Directory patterns (ending with /)
            if pattern.endswith('/'):
                dir_pattern = pattern.rstrip('/')
                # Check if the path starts with the directory pattern
                if path_str.startswith(dir_pattern + '/') or path_str == dir_pattern:
                    return True
                # For single-level patterns, check individual parts
                if '/' not in dir_pattern:
                    if any(fnmatch.fnmatch(part, dir_pattern) for part in path_parts):
                        return True
                # Also check with wildcard matching
                if fnmatch.fnmatch(path_str, dir_pattern + '/*'):
                    return True
            
            # File patterns
            else:
                # Check if pattern matches any part of the path
                if fnmatch.fnmatch(path_str, pattern):
                    return True
                if fnmatch.fnmatch(file_path.name, pattern):
                    return True
                
                # Check if pattern matches any directory component
                if any(fnmatch.fnmatch(part, pattern) for part in path_parts):
                    return True
        
        # Check whitelist patterns (negation)
        for pattern in self.patterns:
            if pattern.startswith('!'):
                whitelist_pattern = pattern[1:]  # Remove the !
                if fnmatch.fnmatch(path_str, whitelist_pattern):
                    return False  # Don't ignore this file
        
        return False
    
    def add_pattern(self, pattern: str) -> None:
        """
        Add a new ignore pattern.
        
        Args:
            pattern: Pattern to add
        """
        self.patterns.add(pattern)
    
    def remove_pattern(self, pattern: str) -> None:
        """
        Remove an ignore pattern.
        
        Args:
            pattern: Pattern to remove
        """
        self.patterns.discard(pattern)
    
    def get_patterns(self) -> List[str]:
        """
        Get all current patterns.
        
        Returns:
            List of all patterns
        """
        return sorted(self.patterns)
    
    def save_ignore_file(self) -> None:
        """Save current patterns to .oopsignore file."""
        ignore_path = self.path_handler.project_root / self.ignore_file
        
        # Filter out default patterns for saving
        custom_patterns = self.patterns - set(self.DEFAULT_PATTERNS)
        
        if not custom_patterns:
            # No custom patterns, remove file if it exists
            if ignore_path.exists():
                ignore_path.unlink()
            return
        
        try:
            with open(ignore_path, 'w', encoding='utf-8') as f:
                f.write("# OOPStracker ignore patterns\n")
                f.write("# This file uses .gitignore syntax\n")
                f.write("# Lines starting with # are comments\n")
                f.write("# Lines starting with ! are whitelist patterns\n\n")
                
                for pattern in sorted(custom_patterns):
                    f.write(f"{pattern}\n")
        except Exception as e:
            print(f"❌ Error writing {ignore_path}: {e}")
    
    def print_patterns(self) -> None:
        """Print all current patterns."""
        print("🚫 Current ignore patterns:")
        print(f"   Default patterns: {len(self.DEFAULT_PATTERNS)}")
        print(f"   Custom patterns: {len(self.patterns - set(self.DEFAULT_PATTERNS))}")
        print(f"   Gitignore patterns: {len(self.gitignore_patterns)}")
        print(f"   Total patterns: {len(self.patterns) + len(self.gitignore_patterns)}")
        
        if self.patterns:
            print("\n   Default/Custom patterns:")
            for pattern in sorted(self.patterns):
                source = "default" if pattern in self.DEFAULT_PATTERNS else "custom"
                print(f"     {pattern:30} ({source})")
        
        if self.gitignore_patterns:
            print("\n   Gitignore patterns:")
            for pattern in sorted(self.gitignore_patterns):
                print(f"     {pattern:30} (gitignore)")