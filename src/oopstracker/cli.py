"""
Command-line interface for OOPStracker.
"""

import argparse
import sys
import json
import logging
from pathlib import Path
from typing import List, Optional

from .core import CodeMemory
from .models import CodeRecord
from .exceptions import OOPSTrackerError


def setup_logging(level: str = "INFO"):
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def scan_file(file_path: str, memory: CodeMemory) -> List[CodeRecord]:
    """Scan a single file for code registration."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Check if duplicate
        result = memory.is_duplicate(code)
        if result.is_duplicate:
            print(f"⚠️  DUPLICATE detected in {file_path}")
            for record in result.matched_records:
                print(f"   Similar to: {record.file_path} (recorded: {record.timestamp})")
            return []
        else:
            # Register new code
            record = memory.register(code, file_path=file_path)
            print(f"✅ Registered: {file_path}")
            return [record]
            
    except Exception as e:
        print(f"❌ Error scanning {file_path}: {e}")
        return []


def scan_directory(directory: str, memory: CodeMemory, pattern: str = "*.py") -> List[CodeRecord]:
    """Scan a directory for Python files."""
    path = Path(directory)
    if not path.exists():
        print(f"❌ Directory does not exist: {directory}")
        return []
    
    records = []
    for file_path in path.rglob(pattern):
        if file_path.is_file():
            records.extend(scan_file(str(file_path), memory))
    
    return records


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="OOPStracker - AI Agent Code Loop Detection and Prevention"
    )
    parser.add_argument(
        "--db", "-d", 
        default="oopstracker.db",
        help="Database file path (default: oopstracker.db)"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=1.0,
        help="Similarity threshold (default: 1.0)"
    )
    parser.add_argument(
        "--log-level", "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan files or directories")
    scan_parser.add_argument(
        "path",
        help="File or directory to scan"
    )
    scan_parser.add_argument(
        "--pattern", "-p",
        default="*.py",
        help="File pattern to match (default: *.py)"
    )
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Check a single code snippet")
    check_parser.add_argument(
        "code",
        help="Code snippet to check"
    )
    
    # Register command
    register_parser = subparsers.add_parser("register", help="Register a code snippet")
    register_parser.add_argument(
        "code",
        help="Code snippet to register"
    )
    register_parser.add_argument(
        "--function-name", "-f",
        help="Function name"
    )
    register_parser.add_argument(
        "--file-path", "-F",
        help="File path"
    )
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all registered code")
    list_parser.add_argument(
        "--format", "-f",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)"
    )
    
    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear all registered code")
    clear_parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    # Initialize code memory
    try:
        memory = CodeMemory(db_path=args.db, threshold=args.threshold)
    except Exception as e:
        print(f"❌ Failed to initialize OOPStracker: {e}")
        sys.exit(1)
    
    # Handle commands
    try:
        if args.command == "scan":
            path = Path(args.path)
            if path.is_file():
                records = scan_file(str(path), memory)
            elif path.is_dir():
                records = scan_directory(str(path), memory, args.pattern)
            else:
                print(f"❌ Invalid path: {args.path}")
                sys.exit(1)
            
            print(f"\n📊 Scanned {len(records)} new code snippets")
            
        elif args.command == "check":
            result = memory.is_duplicate(args.code)
            if result.is_duplicate:
                print("⚠️  DUPLICATE detected!")
                for record in result.matched_records:
                    print(f"   Similar to: {record.file_path} (score: {result.similarity_score})")
            else:
                print("✅ No duplicates found")
                
        elif args.command == "register":
            record = memory.register(
                args.code,
                function_name=args.function_name,
                file_path=args.file_path
            )
            print(f"✅ Registered code with hash: {record.code_hash}")
            
        elif args.command == "list":
            records = memory.get_all_records()
            
            if args.format == "json":
                output = [record.to_dict() for record in records]
                print(json.dumps(output, indent=2, default=str))
            else:
                print(f"\n📋 Found {len(records)} code records:")
                for record in records:
                    print(f"   Hash: {record.code_hash[:16]}...")
                    print(f"   Function: {record.function_name or 'N/A'}")
                    print(f"   File: {record.file_path or 'N/A'}")
                    print(f"   Timestamp: {record.timestamp}")
                    print("   " + "-" * 40)
                    
        elif args.command == "clear":
            if not args.yes:
                confirm = input("Are you sure you want to clear all registered code? (y/N): ")
                if confirm.lower() != 'y':
                    print("Operation cancelled")
                    sys.exit(0)
            
            memory.clear_memory()
            print("✅ Memory cleared successfully")
            
        else:
            parser.print_help()
            
    except OOPSTrackerError as e:
        print(f"❌ OOPStracker error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()