"""Main CLI entry point for OOPStracker using command pattern."""

import sys
import os
import argparse
import asyncio
import logging
from typing import Optional

from .unified_detector import UnifiedDetectionService
from .commands.base import BaseCommand, CommandContext
from .commands.check import CheckCommand


def validate_llm_environment() -> bool:
    """Early validation of LLM environment variables."""
    llm_model = os.getenv("OOPSTRACKER_LLM_MODEL")
    if not llm_model:
        print("❌ LLM configuration required")
        print("\nOOPStracker v3.0+ requires an LLM for semantic analysis.")
        print("Please set the OOPSTRACKER_LLM_MODEL environment variable.")
        print("\n🔧 Quick setup with Ollama:")
        print("   1. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh")
        print("   2. Download model: ollama pull llama2")
        print("   3. Set variable: export OOPSTRACKER_LLM_MODEL='llama2'")
        print("\n📖 See docs/llm_setup.md for detailed instructions")
        return False
    return True


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="oopstracker",
        description="OOPStracker - Code Analysis and Function Clustering"
    )
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        title="Available commands",
        dest="command",
        required=True
    )
    
    # Register commands
    commands = {
        "check": CheckCommand,
    }
    
    for name, command_class in commands.items():
        subparser = subparsers.add_parser(name, help=command_class.help())
        command_class.add_arguments(subparser)
    
    return parser, commands


async def main(argv: Optional[list] = None) -> int:
    """Main CLI entry point."""
    parser, commands = create_parser()
    args = parser.parse_args(argv)
    
    # Early LLM environment validation
    if not validate_llm_environment():
        return 1
    
    # Configure logging
    logging.basicConfig(
        level=logging.WARNING,
        format='%(message)s'
    )
    
    # Initialize detector
    detector = UnifiedDetectionService()
    
    # Create command context
    context = CommandContext(
        detector=detector,
        semantic_detector=None,
        args=args
    )
    
    # Execute command
    command_class = commands[args.command]
    command = command_class(context)
    
    try:
        return await command.execute()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        logging.error(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def cli_main():
    """Synchronous CLI entry point."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    cli_main()