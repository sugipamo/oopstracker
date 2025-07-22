"""
Command-line interface for OOPStracker.
"""

import argparse
import sys
import json
import logging
import asyncio
import os
import contextlib
from pathlib import Path
from typing import List, Optional, Tuple

from .models import CodeRecord
from .exceptions import OOPSTrackerError
from .ignore_patterns import IgnorePatterns
from .ast_simhash_detector import ASTSimHashDetector
from .trivial_filter import TrivialPatternFilter, TrivialFilterConfig
from .semantic_detector import SemanticAwareDuplicateDetector
from .progress_reporter import ProgressReporter
from .commands import CommandContext, COMMAND_REGISTRY
from .utils.logging_setup import setup_logging
from .utils.output_utils import suppress_unwanted_output


async def async_main():
    """Async wrapper for main function."""
    return await _main_impl()


def main():
    """Main entry point for the CLI."""
    # Create and run the event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        exit_code = loop.run_until_complete(async_main())
        sys.exit(exit_code)
    finally:
        loop.close()


async def _main_impl():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="OOPStracker - AI Agent Code Loop Detection and Prevention"
    )
    
    # Global arguments
    parser.add_argument(
        "--db", "-d", 
        default="oopstracker.db",
        help="Database file path (default: oopstracker.db)"
    )
    parser.add_argument(
        "--hamming-threshold", "-t",
        type=int,
        default=10,
        help="Hamming distance threshold for AST SimHash (default: 10)"
    )
    parser.add_argument(
        "--similarity-threshold", "-s",
        type=float,
        default=0.7,
        help="Structural similarity threshold (default: 0.7)"
    )
    parser.add_argument(
        "--semantic-threshold",
        type=float,
        default=0.7,
        help="Semantic similarity threshold (default: 0.7)"
    )
    parser.add_argument(
        "--semantic-timeout",
        type=float,
        default=30.0,
        help="Timeout for semantic analysis in seconds (default: 30.0)"
    )
    parser.add_argument(
        "--max-semantic-concurrent",
        type=int,
        default=3,
        help="Maximum concurrent semantic analyses (default: 3)"
    )
    parser.add_argument(
        "--log-level", "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)"
    )
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Register all commands from the command registry
    for command_name, command_class in COMMAND_REGISTRY.items():
        sub_parser = subparsers.add_parser(command_name, help=command_class.__doc__)
        command_class.add_arguments(sub_parser)
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # If no command specified, show help
    if not args.command:
        parser.print_help()
        return 0
    
    # Initialize detector
    with suppress_unwanted_output():
        detector = ASTSimHashDetector(
            threshold=args.hamming_threshold,
            structural_threshold=args.similarity_threshold,
            db_path=args.db
        )
    
    # Initialize semantic detector
    semantic_detector = SemanticAwareDuplicateDetector(
        structural_detector=detector,
        timeout=args.semantic_timeout
    )
    
    # Create command context
    context = CommandContext(
        detector=detector,
        semantic_detector=semantic_detector,
        args=args
    )
    
    # Handle commands
    try:
        # Use command handler from registry
        if args.command in COMMAND_REGISTRY:
            command_class = COMMAND_REGISTRY[args.command]
            command = command_class(context)
            return await command.execute()
        else:
            parser.print_help()
            return 0
            
    except OOPSTrackerError as e:
        print(f"❌ OOPStracker error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n⏹️  Operation interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.log_level == "DEBUG":
            import traceback
            traceback.print_exc()
        return 1
    finally:
        # Cleanup semantic detector
        await semantic_detector.cleanup()


if __name__ == "__main__":
    main()