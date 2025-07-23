"""
Base command interface for OOPStracker CLI commands.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..unified_detector import UnifiedDetectionService


@dataclass
class CommandContext:
    """Context passed to command handlers."""
    detector: UnifiedDetectionService
    semantic_detector: Optional[Any]
    args: Any  # argparse.Namespace
    
    
class BaseCommand(ABC):
    """Base class for all CLI commands."""
    
    def __init__(self, context: CommandContext):
        self.context = context
        self.detector = context.detector
        self.semantic_detector = context.semantic_detector
        self.args = context.args
        
    @abstractmethod
    async def execute(self) -> int:
        """Execute the command.
        
        Returns:
            Exit code (0 for success)
        """
        pass
        
    @classmethod
    @abstractmethod
    def add_arguments(cls, parser):
        """Add command-specific arguments to the parser."""
        pass
        
    @classmethod
    @abstractmethod
    def help(cls) -> str:
        """Return help text for the command."""
        pass