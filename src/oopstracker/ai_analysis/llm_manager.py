"""
LLM Provider management for AI Analysis.
"""
import logging
from typing import Optional

from llm_providers import create_provider, LLMConfig, PresetManager
from intent_unified.core.semantic_analyzer import SemanticDuplicateAnalyzer, UnifiedConfig


class LLMProviderManager:
    """Manages LLM provider initialization and lifecycle."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._semantic_analyzer = None
        self._llm_provider = None
        self._available = False
        self._initialized = False
    
    async def initialize(self):
        """Initialize LLM components."""
        if self._initialized:
            return
            
        # Create config for semantic analyzer
        unified_config = UnifiedConfig.from_env()
        self._semantic_analyzer = SemanticDuplicateAnalyzer(unified_config)
        
        # Initialize LLM provider using PresetManager
        preset_manager = PresetManager()
        preset = preset_manager.get_default_preset()
        
        if not preset:
            raise RuntimeError("No LLM presets configured. Please use 'llm-providers presets add' to configure an LLM endpoint.")
        
        self.logger.info(f"Using preset '{preset.name}'")
        
        config = LLMConfig(
            provider=preset.provider_type,
            model=preset.model,
            base_url=preset.base_url,
            temperature=preset.temperature,
            max_tokens=preset.max_tokens,
            timeout=preset.timeout,
            retry_count=3,
            retry_delay=0.5
        )
        self._llm_provider = await create_provider(config)
        self._available = True
        self._initialized = True
        self.logger.info(f"LLM provider initialized with preset '{preset.name}' at {config.base_url}")
    
    async def cleanup(self):
        """Clean up resources."""
        if self._llm_provider:
            await self._llm_provider.cleanup()
        if self._semantic_analyzer:
            await self._semantic_analyzer.cleanup()
    
    @property
    def available(self) -> bool:
        """Check if LLM provider is available."""
        return self._available
    
    @property
    def semantic_analyzer(self):
        """Get semantic analyzer instance."""
        if not self._initialized:
            raise RuntimeError("LLM provider not initialized. Call initialize() first.")
        return self._semantic_analyzer
    
    @property
    def llm_provider(self):
        """Get LLM provider instance."""
        if not self._initialized:
            raise RuntimeError("LLM provider not initialized. Call initialize() first.")
        return self._llm_provider
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()