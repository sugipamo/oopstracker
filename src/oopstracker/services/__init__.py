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

__all__ = [
    "CodeNormalizationService",
    "DatabaseOperationsService",
    "ConfigurationService",
    "UnifiedConfig",
    "DatabaseConfig", 
    "AnalysisConfig",
    "DetectionMethod",
    "get_config_service",
    "reset_config_service"
]