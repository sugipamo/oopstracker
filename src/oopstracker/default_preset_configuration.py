"""
Default Preset Configuration - Provides a clear default preset mechanism.
This module addresses the issue of making `oopstracker check` work by default.
"""

from typing import Optional
from dataclasses import dataclass
from llm_providers import LLMPreset


@dataclass
class DefaultPresetConfig:
    """Configuration for default presets."""
    primary_preset_name: str = "gpt-mini"
    fallback_preset_names: list[str] = None
    
    def __post_init__(self):
        if self.fallback_preset_names is None:
            self.fallback_preset_names = ["gpt-4", "local-llama", "ollama-local"]


class DefaultPresetProvider:
    """
    Provides default preset configuration for oopstracker.
    This ensures the tool works out of the box without environment variables.
    """
    
    DEFAULT_PRESETS = {
        "gpt-mini": LLMPreset(
            name="gpt-mini",
            description="OpenAI GPT-3.5 Mini - Efficient and cost-effective",
            base_url="https://api.openai.com/v1",
            model="gpt-3.5-turbo",
            temperature=0.3,
            max_tokens=2048,
            timeout=30.0,
            provider_type="openai",
            tags=["openai", "default", "efficient"]
        ),
        "gpt-4": LLMPreset(
            name="gpt-4",
            description="OpenAI GPT-4 - High quality responses",
            base_url="https://api.openai.com/v1",
            model="gpt-4",
            temperature=0.3,
            max_tokens=4096,
            timeout=60.0,
            provider_type="openai",
            tags=["openai", "premium", "high-quality"]
        ),
        "local-llama": LLMPreset(
            name="local-llama",
            description="Local Llama server - Privacy-focused",
            base_url="http://localhost:8000/v1/chat/completions",
            model="llama2:7b-chat-q4_0",
            temperature=0.3,
            max_tokens=2048,
            timeout=30.0,
            provider_type="llama",
            tags=["local", "llama2", "privacy"]
        )
    }
    
    @classmethod
    def get_default_preset(cls) -> LLMPreset:
        """
        Get the default preset for oopstracker.
        
        Returns:
            Default LLMPreset (gpt-mini)
        """
        return cls.DEFAULT_PRESETS["gpt-mini"]
    
    @classmethod
    def ensure_default_presets_exist(cls, preset_manager) -> None:
        """
        Ensure default presets exist in the preset manager.
        
        Args:
            preset_manager: PresetManager instance to update
        """
        existing_presets = preset_manager.list_presets()
        existing_names = {p.name for p in existing_presets}
        
        # Add missing default presets
        for name, preset in cls.DEFAULT_PRESETS.items():
            if name not in existing_names:
                preset_manager.add_preset(preset)
                print(f"Added default preset: {name}")
    
    @classmethod
    def get_default_config(cls) -> DefaultPresetConfig:
        """Get default configuration."""
        return DefaultPresetConfig()