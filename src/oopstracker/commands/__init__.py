"""
Command handlers for OOPStracker CLI.
"""
from .base import BaseCommand, CommandContext
from .check import CheckCommand
from .register import RegisterCommand
from .list import ListCommand
from .akinator import AkinatorCommand
from .relations import RelationsCommand
from .analyze import AnalyzeCommand
from .clear import ClearCommand

__all__ = [
    'BaseCommand', 
    'CommandContext',
    'CheckCommand',
    'RegisterCommand', 
    'ListCommand',
    'AkinatorCommand',
    'RelationsCommand',
    'AnalyzeCommand',
    'ClearCommand'
]

# コマンドレジストリ
COMMAND_REGISTRY = {
    'check': CheckCommand,
    'register': RegisterCommand,
    'list': ListCommand,
    'akinator': AkinatorCommand,
    'relations': RelationsCommand,
    'analyze': AnalyzeCommand,
    'clear': ClearCommand,
}