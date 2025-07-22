"""
OOPStracker Facade - Simplified interface for external consumers.
Implements the Layer pattern by providing a clean facade over the application layer.
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from .code_analysis_service import CodeAnalysisService
from ..services import ConfigurationService, get_config_service
from ..exceptions import OOPSTrackerError, ValidationError


class OOPSTrackerFacade:
    """
    Simplified facade for OOPStracker functionality.
    
    This facade implements the Layer pattern by providing a clean, 
    simplified interface that hides the complexity of the application
    layer from CLI, API, and other external consumers.
    
    REFACTORED: Replaces the God class UnifiedOOPStracker with proper layered design.
    """
    
    def __init__(self, config_path: Optional[str] = None, **config_overrides):
        """
        Initialize OOPStracker facade.
        
        Args:
            config_path: Optional path to configuration file
            **config_overrides: Configuration overrides
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize configuration service
        self.config_service = get_config_service()
        if config_path:
            self.config_service.config_path = Path(config_path)
        
        # Apply any configuration overrides
        if config_overrides:
            self.config_service.update_config(**config_overrides)
        
        # Initialize application service
        self.analysis_service = CodeAnalysisService(self.config_service)
        
        self.logger.info("OOPStracker facade initialized")
    
    def analyze_path(self, path: str, pattern: str = "*.py") -> Dict[str, Any]:
        """
        Analyze a file or directory for code patterns and duplicates.
        
        Args:
            path: File or directory path to analyze
            pattern: File pattern to match (default: "*.py")
            
        Returns:
            Analysis results with summary and detailed groups
        """
        return self.analysis_service.analyze_path(path, pattern)
    
    def register_code(self, code: str, function_name: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Register a code snippet for duplicate detection.
        
        Args:
            code: Code content to register
            function_name: Name/identifier for the code
            metadata: Optional metadata dictionary
            
        Returns:
            Registration result with success status and record info
        """
        return self.analysis_service.register_code_snippet(code, function_name, metadata)
    
    def check_duplicate(self, code: str) -> Dict[str, Any]:
        """
        Check if code is a duplicate of existing registered code.
        
        Args:
            code: Code content to check
            
        Returns:
            Duplicate detection result with similarity information
        """
        return self.analysis_service.check_duplicate(code)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the analysis system.
        
        Returns:
            Statistics including database info, configuration, and detector status
        """
        return self.analysis_service.get_statistics()
    
    def update_configuration(self, **config_updates) -> Dict[str, Any]:
        """
        Update configuration settings.
        
        Args:
            **config_updates: Configuration updates
            
        Returns:
            Updated configuration status
        """
        try:
            self.config_service.update_config(**config_updates)
            
            # Re-initialize analysis service if detector settings changed
            if any(key in config_updates.get('analysis', {}) 
                   for key in ['detection_method', 'simhash_threshold']):
                self.analysis_service = CodeAnalysisService(self.config_service)
                self.logger.info("Re-initialized analysis service due to configuration changes")
            
            return {
                "success": True,
                "message": "Configuration updated successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Configuration update failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def save_configuration(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Save current configuration to file.
        
        Args:
            config_path: Optional path to save configuration
            
        Returns:
            Save operation result
        """
        try:
            config = self.config_service.get_config()
            self.config_service.save_config(config, config_path)
            return {
                "success": True,
                "message": f"Configuration saved to {config_path or self.config_service.config_path}"
            }
            
        except Exception as e:
            self.logger.error(f"Configuration save failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def load_configuration(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Load operation result
        """
        try:
            config = self.config_service.load_config(config_path)
            
            # Re-initialize analysis service with new configuration
            self.analysis_service = CodeAnalysisService(self.config_service)
            
            return {
                "success": True,
                "message": f"Configuration loaded from {config_path}"
            }
            
        except Exception as e:
            self.logger.error(f"Configuration load failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def reset_database(self) -> Dict[str, Any]:
        """
        Reset the analysis database (clears all data).
        
        Returns:
            Reset operation result
        """
        try:
            db_path = self.config_service.get_database_config().db_path
            db_file = Path(db_path)
            
            if db_file.exists():
                db_file.unlink()
                self.logger.info(f"Deleted database file: {db_path}")
            
            # Re-initialize analysis service to recreate database
            self.analysis_service = CodeAnalysisService(self.config_service)
            
            return {
                "success": True,
                "message": "Database reset successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Database reset failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform system health check.
        
        Returns:
            Health status of all components
        """
        health = {
            "overall_status": "healthy",
            "components": {}
        }
        
        try:
            # Check configuration service
            config = self.config_service.get_config()
            health["components"]["configuration"] = {
                "status": "healthy",
                "db_path": config.database.db_path,
                "detection_method": config.analysis.detection_method.value
            }
            
            # Check database connectivity
            try:
                stats = self.analysis_service.get_statistics()
                health["components"]["database"] = {
                    "status": "healthy",
                    "exists": stats.get("database", {}).get("db_exists", False),
                    "tables": len(stats.get("database", {}).get("tables", []))
                }
            except Exception as e:
                health["components"]["database"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health["overall_status"] = "degraded"
            
            # Check detector status
            try:
                detector_info = self.analysis_service.get_statistics().get("detector_info", {})
                health["components"]["detector"] = {
                    "status": "healthy" if detector_info.get("type") else "not_initialized",
                    "type": detector_info.get("type", "unknown"),
                    "threshold": detector_info.get("threshold")
                }
                
                if not detector_info.get("type"):
                    health["overall_status"] = "degraded"
                    
            except Exception as e:
                health["components"]["detector"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health["overall_status"] = "unhealthy"
            
        except Exception as e:
            health["overall_status"] = "unhealthy"
            health["error"] = str(e)
        
        return health


# Convenience function for quick access
def create_oopstracker(config_path: Optional[str] = None, **config_overrides) -> OOPSTrackerFacade:
    """
    Create an OOPStracker facade instance with optional configuration.
    
    Args:
        config_path: Optional path to configuration file
        **config_overrides: Configuration overrides
        
    Returns:
        Configured OOPSTrackerFacade instance
    """
    return OOPSTrackerFacade(config_path=config_path, **config_overrides)