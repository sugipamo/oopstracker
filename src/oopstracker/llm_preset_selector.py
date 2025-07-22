"""
LLM Preset Selector - Handles the selection of LLM presets with clear business logic.
Follows Single Responsibility Principle and Dependency Inversion Principle.
"""

from typing import Optional, List, Protocol
from abc import ABC, abstractmethod
import logging
import os

from llm_providers import LLMPreset


class PresetSelectionStrategy(ABC):
    """Abstract strategy for selecting a preset from available options."""
    
    @abstractmethod
    def select(self, presets: List[LLMPreset]) -> Optional[LLMPreset]:
        """Select a preset based on the strategy."""
        pass


class EnvironmentVariableStrategy(PresetSelectionStrategy):
    """Select preset based on environment variable."""
    
    def __init__(self, env_var_name: str = "LLM_PRESET"):
        self.env_var_name = env_var_name
        self.logger = logging.getLogger(__name__)
    
    def select(self, presets: List[LLMPreset]) -> Optional[LLMPreset]:
        """Select preset specified by environment variable."""
        preset_name = os.getenv(self.env_var_name)
        if not preset_name:
            return None
            
        for preset in presets:
            if preset.name == preset_name:
                self.logger.info(f"Selected preset '{preset_name}' from environment variable")
                return preset
                
        self.logger.warning(f"Preset '{preset_name}' specified in {self.env_var_name} not found")
        return None


class NamedPresetStrategy(PresetSelectionStrategy):
    """Select preset by specific name."""
    
    def __init__(self, preset_name: str):
        self.preset_name = preset_name
        self.logger = logging.getLogger(__name__)
    
    def select(self, presets: List[LLMPreset]) -> Optional[LLMPreset]:
        """Select preset by name."""
        for preset in presets:
            if preset.name == self.preset_name:
                self.logger.info(f"Selected preset '{self.preset_name}'")
                return preset
        return None


class FirstAvailableStrategy(PresetSelectionStrategy):
    """Select the first available preset."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def select(self, presets: List[LLMPreset]) -> Optional[LLMPreset]:
        """Select first available preset."""
        if presets:
            self.logger.info(f"Selected first available preset: '{presets[0].name}'")
            return presets[0]
        return None


class TagBasedStrategy(PresetSelectionStrategy):
    """Select preset based on tags."""
    
    def __init__(self, required_tags: List[str]):
        self.required_tags = required_tags
        self.logger = logging.getLogger(__name__)
    
    def select(self, presets: List[LLMPreset]) -> Optional[LLMPreset]:
        """Select first preset that has all required tags."""
        for preset in presets:
            if all(tag in preset.tags for tag in self.required_tags):
                self.logger.info(f"Selected preset '{preset.name}' with tags {self.required_tags}")
                return preset
        return None


class CompositeStrategy(PresetSelectionStrategy):
    """Composite strategy that tries multiple strategies in order."""
    
    def __init__(self, strategies: List[PresetSelectionStrategy]):
        self.strategies = strategies
        self.logger = logging.getLogger(__name__)
    
    def select(self, presets: List[LLMPreset]) -> Optional[LLMPreset]:
        """Try each strategy in order until one succeeds."""
        for strategy in self.strategies:
            preset = strategy.select(presets)
            if preset:
                return preset
        return None


class PresetSelector:
    """
    Main selector class that orchestrates preset selection.
    Follows Open/Closed Principle - open for extension via strategies.
    """
    
    def __init__(self, strategy: Optional[PresetSelectionStrategy] = None):
        """
        Initialize with a selection strategy.
        
        Args:
            strategy: Selection strategy to use. If None, uses default strategy.
        """
        self.logger = logging.getLogger(__name__)
        self.strategy = strategy or self._create_default_strategy()
    
    def _create_default_strategy(self) -> PresetSelectionStrategy:
        """Create the default selection strategy."""
        # Default strategy: 
        # 1. Try environment variable
        # 2. Try "gpt-mini" if available
        # 3. Fall back to first available
        return CompositeStrategy([
            EnvironmentVariableStrategy(),
            NamedPresetStrategy("gpt-mini"),
            FirstAvailableStrategy()
        ])
    
    def select_preset(self, presets: List[LLMPreset]) -> LLMPreset:
        """
        Select a preset using the configured strategy.
        
        Args:
            presets: List of available presets
            
        Returns:
            Selected preset
            
        Raises:
            ValueError: If no presets are available or selection fails
        """
        if not presets:
            raise ValueError("No LLM presets available. Please configure at least one preset.")
        
        selected = self.strategy.select(presets)
        
        if not selected:
            # This should rarely happen with default strategy, but handle it gracefully
            self.logger.error("Preset selection strategy failed to select any preset")
            raise ValueError("Failed to select a preset from available options")
        
        return selected
    
    def set_strategy(self, strategy: PresetSelectionStrategy):
        """Change the selection strategy at runtime."""
        self.strategy = strategy


# Factory function for common use cases
def create_default_selector() -> PresetSelector:
    """Create a preset selector with default strategy."""
    return PresetSelector()


def create_production_selector() -> PresetSelector:
    """Create a preset selector optimized for production use."""
    # Production might prefer specific models or tags
    strategy = CompositeStrategy([
        EnvironmentVariableStrategy(),
        TagBasedStrategy(["production", "stable"]),
        NamedPresetStrategy("gpt-4"),
        NamedPresetStrategy("gpt-mini"),
        FirstAvailableStrategy()
    ])
    return PresetSelector(strategy)


def create_development_selector() -> PresetSelector:
    """Create a preset selector optimized for development."""
    # Development might prefer local or cheaper models
    strategy = CompositeStrategy([
        EnvironmentVariableStrategy(),
        TagBasedStrategy(["local", "development"]),
        NamedPresetStrategy("local-llama"),
        NamedPresetStrategy("gpt-mini"),
        FirstAvailableStrategy()
    ])
    return PresetSelector(strategy)