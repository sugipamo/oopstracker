"""
Unified Interface for OOPStracker - Centralizes all functionality into a single, clean API.
This addresses the scattered functionality across 32+ files by providing a single entry point.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Import from existing modules - centralize their usage
# CodeMemory is in core.py file, not in core package
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from core import CodeMemory
from .models import SimilarityResult
from .ast_simhash_detector import ASTSimHashDetector
from .ignore_patterns import IgnorePatterns


@dataclass
class AnalysisConfig:
    """Simplified configuration for analysis."""
    db_path: str = "oopstracker.db"
    threshold: int = 10
    include_tests: bool = False
    use_gitignore: bool = True
    force_scan: bool = False


@dataclass
class AnalysisSummary:
    """Summary of analysis results."""
    total_files: int
    total_functions: int
    duplicate_groups: int
    largest_group_size: int
    analysis_method: str


class UnifiedOOPStracker:
    """
    Unified interface for OOPStracker functionality.
    
    This class centralizes the scattered functionality and provides a clean,
    easy-to-use interface for code analysis operations.
    """
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        self.config = config or AnalysisConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components
        self._detector = None
        self._memory = None
        self._initialize_components()
    
    def analyze_path(self, path: str, pattern: str = "*.py") -> AnalysisSummary:
        """
        Analyze a file or directory for code patterns and duplicates.
        
        Args:
            path: File or directory path to analyze
            pattern: File pattern to match (default: "*.py")
            
        Returns:
            AnalysisSummary with results
        """
        target_path = Path(path)
        
        if not target_path.exists():
            raise ValueError(f"Path does not exist: {path}")
        
        self.logger.info(f"Analyzing: {path}")
        
        # Collect files to analyze
        files_to_analyze = self._collect_files(target_path, pattern)
        
        if not files_to_analyze:
            self.logger.warning("No files found to analyze")
            return AnalysisSummary(
                total_files=0,
                total_functions=0,
                duplicate_groups=0,
                largest_group_size=0,
                analysis_method="none"
            )
        
        # Register files with detector
        total_functions = 0
        for file_path in files_to_analyze:
            try:
                functions = self._detector.register_file(str(file_path))
                if functions:
                    total_functions += len(functions)
                    self.logger.debug(f"Registered {len(functions)} functions from {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to analyze {file_path}: {e}")
        
        # Get analysis results
        clusters = self._get_function_clusters()
        
        return AnalysisSummary(
            total_files=len(files_to_analyze),
            total_functions=total_functions,
            duplicate_groups=len(clusters),
            largest_group_size=max([len(cluster.functions) for cluster in clusters]) if clusters else 0,
            analysis_method="ast_simhash"
        )
    
    def check_duplicate(self, code: str, function_name: Optional[str] = None) -> SimilarityResult:
        """
        Check if given code is a duplicate of existing code.
        
        Args:
            code: Code content to check
            function_name: Optional function name for context
            
        Returns:
            SimilarityResult indicating if code is duplicate
        """
        if not code or not code.strip():
            raise ValueError("Code content cannot be empty")
        
        return self._memory.is_duplicate(code)
    
    def register_code(self, code: str, function_name: Optional[str] = None, 
                     file_path: Optional[str] = None) -> bool:
        """
        Register new code in the system.
        
        Args:
            code: Code content to register
            function_name: Optional function name
            file_path: Optional file path
            
        Returns:
            True if registered successfully
        """
        if not code or not code.strip():
            raise ValueError("Code content cannot be empty")
        
        try:
            self._memory.register(code, function_name, file_path)
            self.logger.debug(f"Registered code: {function_name or 'anonymous'}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to register code: {e}")
            return False
    
    def get_summary(self) -> Dict[str, Any]:
        """Get current analysis summary."""
        all_records = self._memory.get_all_records()
        
        return {
            "total_records": len(all_records),
            "unique_files": len(set(r.file_path for r in all_records if r.file_path)),
            "database_path": self.config.db_path,
            "threshold": self.config.threshold,
            "memory_usage_mb": self._estimate_memory_usage()
        }
    
    def clear_all(self):
        """Clear all stored analysis data."""
        if self._memory:
            self._memory.clear_memory()
        if self._detector:
            self._detector.code_units.clear()
        
        self.logger.info("All analysis data cleared")
    
    def _initialize_components(self):
        """Initialize core components."""
        # Initialize memory storage
        self._memory = CodeMemory(
            db_path=self.config.db_path,
            threshold=self.config.threshold
        )
        
        # Initialize detector
        self._detector = ASTSimHashDetector(
            hamming_threshold=self.config.threshold,
            db_path=self.config.db_path,
            include_tests=self.config.include_tests
        )
    
    def _collect_files(self, target_path: Path, pattern: str) -> List[Path]:
        """Collect files to analyze based on path and pattern."""
        if target_path.is_file():
            return [target_path]
        
        # Initialize ignore patterns
        ignore_patterns = IgnorePatterns(
            project_root=str(target_path),
            use_gitignore=self.config.use_gitignore,
            include_tests=self.config.include_tests
        )
        
        files = []
        for file_path in target_path.rglob(pattern):
            if file_path.is_file() and not ignore_patterns.should_ignore(file_path):
                files.append(file_path)
        
        return files
    
    def _get_function_clusters(self) -> List:
        """Get function clusters from detector."""
        # Use existing clustering functionality if available
        if hasattr(self._detector, 'code_units'):
            # Group similar functions - simplified clustering
            all_functions = [unit for unit in self._detector.code_units.values() if unit.type == 'function']
            
            # Simple grouping by similarity (placeholder)
            clusters = []
            if all_functions:
                # For now, return a single cluster with all functions
                cluster = type('Cluster', (), {})()
                cluster.functions = all_functions
                clusters.append(cluster)
            
            return clusters
        
        return []
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB."""
        # Simple estimation based on number of records
        record_count = len(self._memory.get_all_records()) if self._memory else 0
        estimated_mb = (record_count * 2048) / (1024 * 1024)  # Rough estimate
        return round(estimated_mb, 2)