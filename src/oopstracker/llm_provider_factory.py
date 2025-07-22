"""
LLM Provider Factory with lazy import and better error handling.
Extracted from ai_analysis_coordinator.py as part of Extract pattern refactoring.
"""

import logging
from typing import Optional, Any
from abc import ABC, abstractmethod


class LLMProviderInterface(ABC):
    """Interface for LLM providers."""
    
    @abstractmethod
    async def generate(self, prompt: str) -> Any:
        """Generate response from prompt."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass


class StubLLMProvider(LLMProviderInterface):
    """Stub implementation when LLM is not available."""
    
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.logger.warning("Using stub LLM provider - no actual LLM functionality available")
    
    async def generate(self, prompt: str) -> Any:
        raise RuntimeError(
            "LLM provider is not available. Please install and configure llm-providers package."
        )
    
    async def cleanup(self) -> None:
        pass


class LLMProviderFactory:
    """Factory for creating LLM providers with lazy import."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._provider_module = None
        self._llm_available = None
        self._import_error = None
    
    def _import_llm_providers(self) -> bool:
        """Lazy import of llm_providers module."""
        if self._llm_available is not None:
            return self._llm_available
            
        try:
            import llm_providers
            self._provider_module = llm_providers
            self._llm_available = True
            self.logger.debug("Successfully imported llm_providers")
        except ImportError as e:
            self._provider_module = None
            self._llm_available = False
            self._import_error = str(e)
            self.logger.debug(f"Failed to import llm_providers: {e}")
            
        return self._llm_available
    
    def is_available(self) -> bool:
        """Check if LLM functionality is available."""
        return self._import_llm_providers()
    
    def get_import_error(self) -> Optional[str]:
        """Get import error message if any."""
        self._import_llm_providers()
        return self._import_error
    
    async def create_provider(self, config: Optional[Any] = None) -> LLMProviderInterface:
        """Create LLM provider instance."""
        if not self._import_llm_providers():
            self.logger.warning(
                f"LLM providers not available: {self._import_error}. "
                "Using stub implementation."
            )
            return StubLLMProvider()
        
        # If no config provided, try to use default preset
        if config is None:
            config = await self._create_default_config()
            if config is None:
                return StubLLMProvider()
        
        try:
            provider = await self._provider_module.create_provider(config)
            self.logger.info("Successfully created LLM provider")
            return provider
        except Exception as e:
            self.logger.error(f"Failed to create LLM provider: {e}")
            return StubLLMProvider()
    
    async def _create_default_config(self) -> Optional[Any]:
        """Create default config using PresetManager."""
        try:
            preset_manager = self._provider_module.PresetManager()
            preset = preset_manager.get_default_preset()
            
            if not preset:
                self.logger.warning(
                    "No LLM presets configured. Please use 'llm-providers presets add' "
                    "to configure an LLM endpoint."
                )
                return None
            
            self.logger.info(f"Using preset '{preset.name}'")
            
            config = self._provider_module.LLMConfig(
                provider=preset.provider_type,
                model=preset.model,
                base_url=preset.base_url,
                temperature=preset.temperature,
                max_tokens=preset.max_tokens,
                timeout=preset.timeout,
                retry_count=3,
                retry_delay=0.5
            )
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to create default config: {e}")
            return None
    
    def get_config_class(self) -> Optional[type]:
        """Get LLMConfig class if available."""
        if not self._import_llm_providers():
            return None
        return getattr(self._provider_module, 'LLMConfig', None)
    
    def get_preset_manager_class(self) -> Optional[type]:
        """Get PresetManager class if available."""
        if not self._import_llm_providers():
            return None
        return getattr(self._provider_module, 'PresetManager', None)