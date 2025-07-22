"""
Configuration Service - Centralized configuration management.
Implements the Centralize pattern to unify scattered configuration classes.
"""

import os
import json
import logging
from dataclasses import dataclass, asdict, fields
from pathlib import Path
from typing import Dict, Any, Optional, Union, Type, TypeVar
from enum import Enum

from ..exceptions import ConfigurationError

T = TypeVar('T')


class DetectionMethod(Enum):
    """Detection methods available in OOPStracker."""
    SIMHASH = "simhash"
    AST = "ast" 
    HYBRID = "hybrid"
    SEMANTIC = "semantic"


@dataclass
class DatabaseConfig:
    """Unified database configuration."""
    db_path: str = "oopstracker.db"
    create_tables: bool = True
    backup_enabled: bool = True
    backup_interval: int = 3600  # seconds
    max_records: Optional[int] = None
    connection_timeout: float = 30.0


@dataclass 
class AnalysisConfig:
    """Unified analysis configuration."""
    # Detection settings
    detection_method: DetectionMethod = DetectionMethod.HYBRID
    simhash_threshold: int = 10
    include_tests: bool = False
    use_gitignore: bool = True
    force_scan: bool = False
    
    # AI Analysis settings
    use_ai_analysis: bool = True
    ai_timeout: float = 30.0
    
    # Performance settings
    max_files_per_batch: int = 100
    parallel_processing: bool = True
    max_workers: int = 4


@dataclass
class UnifiedConfig:
    """Master configuration combining all settings."""
    database: DatabaseConfig
    analysis: AnalysisConfig
    
    # Global settings
    log_level: str = "INFO"
    debug_mode: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.analysis.simhash_threshold < 0:
            raise ConfigurationError("simhash_threshold must be non-negative")
        if self.analysis.ai_timeout <= 0:
            raise ConfigurationError("ai_timeout must be positive")
        if self.analysis.max_workers < 1:
            raise ConfigurationError("max_workers must be at least 1")


class ConfigurationService:
    """
    Centralized configuration management service.
    
    This service centralizes configuration management that was scattered across:
    - models.py:120-139 (DatabaseConfig)
    - domain/models.py:37-47 (AnalysisConfig) 
    - unified_interface.py:18-25 (AnalysisConfig duplicate)
    - llm_configuration_manager.py:26-34 (LLMConfiguration)
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.config_path = Path(config_path) if config_path else None
        self._config: Optional[UnifiedConfig] = None
    
    def get_config(self) -> UnifiedConfig:
        """Get the current configuration, loading from file if needed."""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def load_config(self, config_path: Optional[str] = None) -> UnifiedConfig:
        """
        Load configuration from file or environment variables.
        
        Args:
            config_path: Optional path to configuration file
            
        Returns:
            UnifiedConfig instance
        """
        config_file = Path(config_path) if config_path else self.config_path
        
        # Start with defaults
        database_config = DatabaseConfig()
        analysis_config = AnalysisConfig()
        
        # Load from file if exists
        if config_file and config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                database_config = self._dict_to_dataclass(data.get('database', {}), DatabaseConfig)
                analysis_config = self._dict_to_dataclass(data.get('analysis', {}), AnalysisConfig)
                self.logger.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                self.logger.warning(f"Failed to load config from {config_file}: {e}")
        
        # Override with environment variables
        database_config = self._apply_env_overrides(database_config, 'OOPSTRACKER_DB_')
        analysis_config = self._apply_env_overrides(analysis_config, 'OOPSTRACKER_ANALYSIS_')
        
        # Create global config
        global_settings = {
            'log_level': os.getenv('OOPSTRACKER_LOG_LEVEL', 'INFO'),
            'debug_mode': os.getenv('OOPSTRACKER_DEBUG', 'false').lower() == 'true'
        }
        
        return UnifiedConfig(
            database=database_config,
            analysis=analysis_config,
            **global_settings
        )
    
    def save_config(self, config: UnifiedConfig, config_path: Optional[str] = None) -> None:
        """
        Save configuration to file.
        
        Args:
            config: Configuration to save
            config_path: Optional path to save to
        """
        config_file = Path(config_path) if config_path else self.config_path
        
        if not config_file:
            raise ConfigurationError("No config path specified")
        
        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'database': asdict(config.database),
                'analysis': asdict(config.analysis),
                'log_level': config.log_level,
                'debug_mode': config.debug_mode
            }
            
            # Convert enums to strings for JSON serialization
            if 'detection_method' in data['analysis']:
                data['analysis']['detection_method'] = data['analysis']['detection_method'].value
            
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            self.logger.info(f"Saved configuration to {config_file}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save config to {config_file}: {e}")
    
    def _dict_to_dataclass(self, data: Dict[str, Any], dataclass_type: Type[T]) -> T:
        """Convert dictionary to dataclass, handling type conversions."""
        # Get field names and types
        field_names = {f.name for f in fields(dataclass_type)}
        
        # Filter data to only include valid fields
        filtered_data = {k: v for k, v in data.items() if k in field_names}
        
        # Handle enum conversions
        if 'detection_method' in filtered_data and dataclass_type == AnalysisConfig:
            if isinstance(filtered_data['detection_method'], str):
                try:
                    filtered_data['detection_method'] = DetectionMethod(filtered_data['detection_method'])
                except ValueError:
                    self.logger.warning(f"Invalid detection_method: {filtered_data['detection_method']}")
                    filtered_data.pop('detection_method')
        
        return dataclass_type(**filtered_data)
    
    def _apply_env_overrides(self, config: T, prefix: str) -> T:
        """Apply environment variable overrides to configuration."""
        config_dict = asdict(config)
        
        for field in fields(config):
            env_key = f"{prefix}{field.name.upper()}"
            env_value = os.getenv(env_key)
            
            if env_value is not None:
                # Convert string environment variable to appropriate type
                try:
                    if field.type == bool:
                        config_dict[field.name] = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif field.type == int:
                        config_dict[field.name] = int(env_value)
                    elif field.type == float:
                        config_dict[field.name] = float(env_value)
                    elif field.type == DetectionMethod:
                        config_dict[field.name] = DetectionMethod(env_value)
                    else:
                        config_dict[field.name] = env_value
                        
                    self.logger.debug(f"Applied env override: {env_key}={env_value}")
                        
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Failed to parse env var {env_key}={env_value}: {e}")
        
        return type(config)(**config_dict)
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration."""
        return self.get_config().database
    
    def get_analysis_config(self) -> AnalysisConfig:
        """Get analysis configuration."""
        return self.get_config().analysis
    
    def update_config(self, **kwargs) -> None:
        """Update configuration with new values."""
        config = self.get_config()
        
        # Update database settings
        if 'database' in kwargs:
            for key, value in kwargs['database'].items():
                if hasattr(config.database, key):
                    setattr(config.database, key, value)
        
        # Update analysis settings  
        if 'analysis' in kwargs:
            for key, value in kwargs['analysis'].items():
                if hasattr(config.analysis, key):
                    setattr(config.analysis, key, value)
        
        # Update global settings
        for key, value in kwargs.items():
            if key not in ('database', 'analysis') and hasattr(config, key):
                setattr(config, key, value)
        
        self._config = config


# Global configuration service instance
_config_service: Optional[ConfigurationService] = None


def get_config_service() -> ConfigurationService:
    """Get the global configuration service instance."""
    global _config_service
    if _config_service is None:
        _config_service = ConfigurationService()
    return _config_service


def reset_config_service() -> None:
    """Reset the global configuration service (mainly for testing)."""
    global _config_service
    _config_service = None