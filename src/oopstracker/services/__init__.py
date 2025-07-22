"""
Services package for OOPStracker.
Contains extracted service classes following the Extract pattern.
"""

from .code_normalization_service import CodeNormalizationService
from .database_operations_service import DatabaseOperationsService  
from .configuration_service import (
    ConfigurationService, 
    UnifiedConfig, 
    DatabaseConfig, 
    AnalysisConfig,
    DetectionMethod,
    get_config_service,
    reset_config_service
)
from .file_scan_service import FileScanService
from .duplicate_detection_service import DuplicateDetectionService
from .classification_service import ClassificationService
from .clustering_service import ClusteringService

__all__ = [
    "CodeNormalizationService",
    "DatabaseOperationsService",
    "ConfigurationService",
    "UnifiedConfig",
    "DatabaseConfig", 
    "AnalysisConfig",
    "DetectionMethod",
    "get_config_service",
    "reset_config_service",
    "FileScanService",
    "DuplicateDetectionService",
    "ClassificationService",
    "ClusteringService"
]