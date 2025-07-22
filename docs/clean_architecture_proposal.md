# Clean Architecture Proposal for oopstracker

## Executive Summary

This proposal addresses the architectural issues in oopstracker's AI coordination layer, specifically:
- The complex one-liner for preset selection (lines 347-348)
- Lack of clear default preset mechanism
- Mixed responsibilities in AIAnalysisCoordinator
- Poor separation of concerns

## Problems Identified

### 1. Complex One-liner (ai_analysis_coordinator.py:347-348)
```python
# OLD - Confusing and hard to maintain
preset = next((p for p in presets if p.name == "gpt-mini"), presets[0])
```

This violates:
- **Readability**: Complex logic compressed into one line
- **Maintainability**: Hard to modify selection logic
- **Testability**: Difficult to unit test

### 2. Mixed Responsibilities
The `AIAnalysisCoordinator` class handles:
- AI analysis coordination (primary responsibility)
- Preset selection logic (should be separate)
- Configuration management (should be separate)
- LLM provider lifecycle (should be separate)

### 3. No Clear Default Mechanism
- Relies on environment variables
- Hardcoded "gpt-mini" preference
- No clear fallback strategy

## Proposed Solution

### 1. Strategy Pattern for Preset Selection

**File: `llm_preset_selector.py`**

```python
class PresetSelectionStrategy(ABC):
    """Abstract strategy for selecting a preset."""
    @abstractmethod
    def select(self, presets: List[LLMPreset]) -> Optional[LLMPreset]:
        pass

class CompositeStrategy(PresetSelectionStrategy):
    """Tries multiple strategies in order."""
    def __init__(self, strategies: List[PresetSelectionStrategy]):
        self.strategies = strategies
    
    def select(self, presets: List[LLMPreset]) -> Optional[LLMPreset]:
        for strategy in self.strategies:
            preset = strategy.select(presets)
            if preset:
                return preset
        return None
```

### 2. Configuration Manager with Dependency Injection

**File: `llm_configuration_manager.py`**

```python
class LLMConfigurationManager:
    """Manages LLM configuration lifecycle."""
    
    def __init__(
        self,
        preset_manager: Optional[PresetManager] = None,
        preset_selector: Optional[PresetSelector] = None
    ):
        self.preset_manager = preset_manager or PresetManager()
        self.preset_selector = preset_selector or create_default_selector()
    
    def get_configuration(self) -> LLMConfiguration:
        """Get LLM configuration using clean selection logic."""
        presets = self.preset_manager.list_presets()
        selected_preset = self.preset_selector.select_preset(presets)
        return self._create_configuration(selected_preset)
```

### 3. Default Preset Provider

**File: `default_preset_configuration.py`**

```python
class DefaultPresetProvider:
    """Provides default presets for out-of-box functionality."""
    
    DEFAULT_PRESETS = {
        "gpt-mini": LLMPreset(...),
        "gpt-4": LLMPreset(...),
        "local-llama": LLMPreset(...)
    }
    
    @classmethod
    def ensure_default_presets_exist(cls, preset_manager):
        """Ensure defaults exist in preset manager."""
        # Add missing defaults
```

### 4. Refactored AI Coordinator

**File: `ai_analysis_coordinator_refactored.py`**

```python
class AIAnalysisCoordinator(AIAnalysisInterface):
    """Coordinates AI analysis with clean separation of concerns."""
    
    def __init__(self, config_manager: Optional[LLMConfigurationManager] = None):
        self._config_manager = config_manager or LLMConfigurationManager()
        # Other initialization...
    
    async def _ensure_initialized(self):
        """Clean initialization without complex logic."""
        config = self._config_manager.get_configuration()
        self._llm_provider = await self._config_manager.get_provider()
        # No complex preset selection here!
```

## Benefits

### 1. SOLID Principles Compliance

- **Single Responsibility**: Each class has one clear purpose
- **Open/Closed**: Easy to add new selection strategies
- **Liskov Substitution**: Strategies are interchangeable
- **Interface Segregation**: Clean protocols and interfaces
- **Dependency Inversion**: Depends on abstractions

### 2. Clean Code Practices

- **No complex one-liners**: Clear, readable logic
- **Explicit over implicit**: Selection strategy is clear
- **Testable**: Each component can be tested independently
- **Configurable**: Easy to change behavior

### 3. Out-of-Box Functionality

```bash
# Works without any environment variables!
oopstracker check

# System automatically:
# 1. Checks LLM_PRESET env var
# 2. Tries gpt-mini if available  
# 3. Falls back to first available preset
```

## Migration Path

1. **Phase 1**: Add new components without breaking existing code
   - Create `llm_preset_selector.py`
   - Create `llm_configuration_manager.py`
   - Create `default_preset_configuration.py`

2. **Phase 2**: Refactor AIAnalysisCoordinator
   - Create `ai_analysis_coordinator_refactored.py`
   - Test thoroughly with existing functionality

3. **Phase 3**: Replace old implementation
   - Update imports in dependent modules
   - Remove old complex logic
   - Update documentation

## Code Comparison

### Before (Complex)
```python
# Confusing one-liner with nested logic
preset = next((p for p in presets if p.name == "gpt-mini"), presets[0])
```

### After (Clean)
```python
# Clear and extensible
preset = self.preset_selector.select_preset(presets)
```

## Testing Strategy

```python
# Easy to test each component
def test_env_var_strategy():
    strategy = EnvironmentVariableStrategy()
    os.environ["LLM_PRESET"] = "test-preset"
    result = strategy.select([test_preset])
    assert result.name == "test-preset"

def test_composite_strategy():
    strategy = CompositeStrategy([
        NamedPresetStrategy("missing"),
        NamedPresetStrategy("gpt-mini"),
        FirstAvailableStrategy()
    ])
    result = strategy.select(presets)
    assert result.name == "gpt-mini"
```

## Conclusion

This clean architecture proposal:
- ✅ Eliminates complex one-liners
- ✅ Provides clear separation of concerns
- ✅ Makes the tool work by default
- ✅ Follows SOLID principles
- ✅ Improves testability and maintainability
- ✅ Provides flexibility for future enhancements

The refactored code is more maintainable, testable, and follows established design patterns while solving the immediate problems identified in the codebase.