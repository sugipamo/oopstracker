"""
LLM Configuration Manager - Manages LLM configuration with proper separation of concerns.
Follows Interface Segregation Principle and Dependency Inversion Principle.
"""

from typing import Optional, Protocol
from dataclasses import dataclass
import logging

from llm_providers import PresetManager, LLMConfig, create_provider
from .llm_preset_selector import PresetSelector, create_default_selector


class LLMProviderProtocol(Protocol):
    """Protocol for LLM providers to ensure loose coupling."""
    
    async def generate(self, prompt: str) -> Any:
        """Generate response from prompt."""
        ...
    
    async def cleanup(self):
        """Clean up resources."""
        ...


@dataclass
class LLMConfiguration:
    """Configuration data for LLM setup."""
    preset_name: str
    config: LLMConfig
    provider_type: str
    
    def __str__(self) -> str:
        return f"LLMConfiguration(preset='{self.preset_name}', model='{self.config.model}', url='{self.config.base_url}')"


class LLMConfigurationManager:
    """
    Manages LLM configuration lifecycle.
    Single Responsibility: Configure and provide LLM instances.
    """
    
    def __init__(
        self,
        preset_manager: Optional[PresetManager] = None,
        preset_selector: Optional[PresetSelector] = None
    ):
        """
        Initialize configuration manager with dependencies.
        
        Args:
            preset_manager: PresetManager instance (injected dependency)
            preset_selector: PresetSelector instance (injected dependency)
        """
        self.logger = logging.getLogger(__name__)
        self.preset_manager = preset_manager or PresetManager()
        self.preset_selector = preset_selector or create_default_selector()
        self._current_config: Optional[LLMConfiguration] = None
        self._provider: Optional[LLMProviderProtocol] = None
    
    def get_configuration(self) -> LLMConfiguration:
        """
        Get LLM configuration using clean selection logic.
        
        Returns:
            LLMConfiguration object
            
        Raises:
            RuntimeError: If no presets are configured
        """
        # Get available presets
        presets = self.preset_manager.list_presets()
        
        if not presets:
            raise RuntimeError(
                "No LLM presets configured. Please use 'llm-providers presets add' "
                "to configure an LLM endpoint."
            )
        
        # Use selector to choose preset
        selected_preset = self.preset_selector.select_preset(presets)
        
        # Create configuration
        config = LLMConfig(
            provider=selected_preset.provider_type,
            model=selected_preset.model,
            base_url=selected_preset.base_url,
            temperature=selected_preset.temperature,
            max_tokens=selected_preset.max_tokens,
            timeout=selected_preset.timeout,
            retry_count=3,
            retry_delay=0.5
        )
        
        self._current_config = LLMConfiguration(
            preset_name=selected_preset.name,
            config=config,
            provider_type=selected_preset.provider_type
        )
        
        self.logger.info(f"Configured LLM: {self._current_config}")
        
        return self._current_config
    
    async def get_provider(self) -> LLMProviderProtocol:
        """
        Get or create LLM provider instance.
        
        Returns:
            LLM provider instance
            
        Raises:
            RuntimeError: If provider creation fails
        """
        if self._provider:
            return self._provider
        
        if not self._current_config:
            self.get_configuration()
        
        try:
            self._provider = await create_provider(self._current_config.config)
            return self._provider
        except Exception as e:
            self.logger.error(f"Failed to create LLM provider: {e}")
            raise RuntimeError(f"Cannot create LLM provider: {e}")
    
    async def cleanup(self):
        """Clean up resources."""
        if self._provider:
            await self._provider.cleanup()
            self._provider = None
        self._current_config = None
    
    @property
    def is_configured(self) -> bool:
        """Check if LLM is configured."""
        return self._current_config is not None
    
    @property
    def current_preset_name(self) -> Optional[str]:
        """Get current preset name if configured."""
        return self._current_config.preset_name if self._current_config else None


class LLMConfigurationError(Exception):
    """Raised when LLM configuration fails."""
    pass