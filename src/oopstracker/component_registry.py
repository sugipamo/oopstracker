"""
Component registry for explicit dependency management.
"""

from typing import Dict, Any, Type, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class ComponentDescriptor:
    """Descriptor for component registration."""
    component_type: Type
    is_available: bool
    initialization_params: Dict[str, Any]
    error_message: str = ""


class ComponentProvider(ABC):
    """Abstract provider for components."""
    
    @abstractmethod
    def get_component_type(self) -> str:
        """Return component type identifier."""
        pass
    
    @abstractmethod
    def create_component(self, **params) -> Any:
        """Create component instance."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if component can be created."""
        pass


class DatabaseManagerProvider(ComponentProvider):
    """Provider for database manager."""
    
    def get_component_type(self) -> str:
        return "database_manager"
    
    def create_component(self, **params) -> Any:
        from .database.connection_manager import DatabaseConnectionManager
        db_path = params.get('db_path', 'oopstracker.db')
        return DatabaseConnectionManager(db_path)
    
    def is_available(self) -> bool:
        return True


class ComponentRegistry:
    """Registry for managing component providers."""
    
    def __init__(self):
        self._providers: Dict[str, ComponentProvider] = {}
        self._register_default_providers()
    
    def _register_default_providers(self):
        """Register default available providers."""
        self.register_provider(DatabaseManagerProvider())
    
    def register_provider(self, provider: ComponentProvider):
        """Register a component provider."""
        component_type = provider.get_component_type()
        if provider.is_available():
            self._providers[component_type] = provider
    
    def create_component(self, component_type: str, **params) -> Optional[Any]:
        """Create component by type."""
        provider = self._providers.get(component_type)
        if provider:
            return provider.create_component(**params)
        return None
    
    def is_component_available(self, component_type: str) -> bool:
        """Check if component type is available."""
        return component_type in self._providers
    
    def get_available_components(self) -> Dict[str, bool]:
        """Get all available component types."""
        return {
            component_type: True 
            for component_type in self._providers.keys()
        }