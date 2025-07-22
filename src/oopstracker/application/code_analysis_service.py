"""
Code Analysis Service - Application layer for orchestrating code analysis operations.
Implements the Layer pattern to separate business logic from presentation layer.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Iterator
from dataclasses import asdict

from ..services import (
    CodeNormalizationService, 
    DatabaseOperationsService, 
    ConfigurationService,
    AnalysisConfig,
    DatabaseConfig
)
from ..models import CodeRecord, SimilarityResult
from ..ast_simhash_detector import ASTSimHashDetector
from ..ignore_patterns import IgnorePatterns
from ..exceptions import OOPSTrackerError, ValidationError


class CodeAnalysisService:
    """
    Application service for code analysis operations.
    
    This service implements the Layer pattern by separating business logic
    from the presentation layer (CLI/API) and coordinating between domain
    services and infrastructure concerns.
    
    Responsibilities:
    - Orchestrate code analysis workflows
    - Coordinate between multiple detection strategies
    - Handle file collection and filtering
    - Manage analysis results and reporting
    """
    
    def __init__(self, config_service: ConfigurationService):
        self.config_service = config_service
        self.logger = logging.getLogger(__name__)
        
        # Initialize services
        self.normalization_service = CodeNormalizationService()
        self.database_service = DatabaseOperationsService(
            config_service.get_database_config().db_path
        )
        
        # Initialize detectors (will be configured based on analysis config)
        self._detector = None
        self._initialize_detector()
    
    def _initialize_detector(self):
        """Initialize the appropriate detector based on configuration."""
        analysis_config = self.config_service.get_analysis_config()
        
        if analysis_config.detection_method.value in ['ast', 'hybrid']:
            self._detector = ASTSimHashDetector(threshold=analysis_config.simhash_threshold)
            self.logger.info(f"Initialized AST detector with threshold {analysis_config.simhash_threshold}")
        else:
            # Fallback to basic detector
            from ..simhash_detector import SimHashSimilarityDetector
            self._detector = SimHashSimilarityDetector(threshold=analysis_config.simhash_threshold)
            self.logger.info(f"Initialized SimHash detector with threshold {analysis_config.simhash_threshold}")
    
    def analyze_path(self, target_path: str, file_pattern: str = "*.py") -> Dict[str, Any]:
        """
        Analyze a file or directory for code patterns and duplicates.
        
        Args:
            target_path: Path to analyze
            file_pattern: File pattern to match
            
        Returns:
            Analysis results dictionary
        """
        try:
            path = Path(target_path)
            if not path.exists():
                raise ValidationError(f"Path does not exist: {target_path}")
            
            self.logger.info(f"Starting analysis of: {target_path}")
            
            # Collect files to analyze
            files = list(self._collect_files(path, file_pattern))
            if not files:
                self.logger.warning("No files found to analyze")
                return self._create_empty_result()
            
            # Process files
            total_functions = 0
            processed_files = 0
            
            for file_path in files:
                try:
                    functions = self._process_file(file_path)
                    if functions:
                        total_functions += len(functions)
                        processed_files += 1
                        self.logger.debug(f"Processed {len(functions)} functions from {file_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to process {file_path}: {e}")
            
            # Analyze for duplicates
            duplicate_groups = self._find_duplicate_groups()
            
            return {
                "success": True,
                "total_files": len(files),
                "processed_files": processed_files,
                "total_functions": total_functions,
                "duplicate_groups": len(duplicate_groups),
                "largest_group_size": max([len(group) for group in duplicate_groups], default=0),
                "analysis_method": self.config_service.get_analysis_config().detection_method.value,
                "groups": duplicate_groups
            }
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_files": 0,
                "processed_files": 0,
                "total_functions": 0,
                "duplicate_groups": 0,
                "largest_group_size": 0,
                "analysis_method": "failed"
            }
    
    def register_code_snippet(self, code: str, function_name: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Register a code snippet for duplicate detection.
        
        Args:
            code: Code content to register
            function_name: Name/identifier for the code
            metadata: Optional metadata
            
        Returns:
            Registration result
        """
        try:
            # Normalize code
            normalized = self.normalization_service.normalize_code(code)
            
            # Create record
            record = CodeRecord(
                code_content=code,
                normalized_code=normalized,
                function_name=function_name,
                metadata=metadata or {}
            )
            record.generate_hash()
            
            # Register with detector
            if hasattr(self._detector, 'register'):
                result = self._detector.register(code, function_name)
                return {
                    "success": True,
                    "record_id": result.id if hasattr(result, 'id') else None,
                    "code_hash": record.code_hash,
                    "function_name": function_name
                }
            else:
                raise OOPSTrackerError("Detector does not support registration")
                
        except Exception as e:
            self.logger.error(f"Code registration failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_duplicate(self, code: str) -> Dict[str, Any]:
        """
        Check if code is a duplicate of existing registered code.
        
        Args:
            code: Code to check
            
        Returns:
            Duplicate check result
        """
        try:
            if hasattr(self._detector, 'is_duplicate'):
                result = self._detector.is_duplicate(code)
                return {
                    "success": True,
                    "is_duplicate": result.is_duplicate if hasattr(result, 'is_duplicate') else False,
                    "similarity_score": result.similarity_score if hasattr(result, 'similarity_score') else 0.0,
                    "similar_records": result.similar_records if hasattr(result, 'similar_records') else []
                }
            else:
                return {
                    "success": False,
                    "error": "Detector does not support duplicate checking"
                }
                
        except Exception as e:
            self.logger.error(f"Duplicate check failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _collect_files(self, path: Path, pattern: str) -> Iterator[Path]:
        """Collect files matching the pattern, respecting ignore patterns."""
        analysis_config = self.config_service.get_analysis_config()
        
        # Initialize ignore patterns
        ignore_patterns = IgnorePatterns(
            use_gitignore=analysis_config.use_gitignore,
            include_tests=analysis_config.include_tests
        )
        
        if path.is_file():
            if not ignore_patterns.should_ignore(path):
                yield path
        else:
            # Walk directory
            for file_path in path.rglob(pattern):
                if file_path.is_file() and not ignore_patterns.should_ignore(file_path):
                    yield file_path
    
    def _process_file(self, file_path: Path) -> Optional[List[Any]]:
        """Process a single file and extract functions."""
        try:
            if hasattr(self._detector, 'register_file'):
                return self._detector.register_file(str(file_path))
            else:
                # Fallback: read file content and register as single unit
                content = file_path.read_text(encoding='utf-8')
                self.register_code_snippet(content, str(file_path))
                return [content]  # Return as single-item list
                
        except Exception as e:
            self.logger.warning(f"Failed to process file {file_path}: {e}")
            return None
    
    def _find_duplicate_groups(self) -> List[List[Dict[str, Any]]]:
        """Find groups of duplicate functions."""
        try:
            if hasattr(self._detector, 'get_duplicate_groups'):
                return self._detector.get_duplicate_groups()
            elif hasattr(self._detector, 'find_similar_pairs'):
                # Convert pairs to groups
                pairs = self._detector.find_similar_pairs()
                return self._pairs_to_groups(pairs)
            else:
                self.logger.warning("Detector does not support duplicate group detection")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to find duplicate groups: {e}")
            return []
    
    def _pairs_to_groups(self, pairs: List[Any]) -> List[List[Dict[str, Any]]]:
        """Convert similarity pairs to groups."""
        # This is a simplified grouping algorithm
        # In practice, you might want to use a more sophisticated approach
        groups = []
        processed = set()
        
        for pair in pairs:
            if hasattr(pair, 'record') and hasattr(pair, 'similar_record'):
                record1, record2 = pair.record, pair.similar_record
                
                if record1 not in processed and record2 not in processed:
                    group = [
                        {"function_name": getattr(record1, 'function_name', 'unknown')},
                        {"function_name": getattr(record2, 'function_name', 'unknown')}
                    ]
                    groups.append(group)
                    processed.add(record1)
                    processed.add(record2)
        
        return groups
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """Create empty analysis result."""
        return {
            "success": True,
            "total_files": 0,
            "processed_files": 0,
            "total_functions": 0,
            "duplicate_groups": 0,
            "largest_group_size": 0,
            "analysis_method": "none",
            "groups": []
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get analysis statistics."""
        try:
            db_stats = self.database_service.get_database_stats()
            config = self.config_service.get_config()
            
            return {
                "database": db_stats,
                "configuration": {
                    "detection_method": config.analysis.detection_method.value,
                    "threshold": config.analysis.simhash_threshold,
                    "database_path": config.database.db_path
                },
                "detector_info": {
                    "type": type(self._detector).__name__ if self._detector else "none",
                    "threshold": getattr(self._detector, 'threshold', None)
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}