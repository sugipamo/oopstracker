"""
Command-line interface for OOPStracker.
"""

import argparse
import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Optional

from .models import CodeRecord
from .exceptions import OOPSTrackerError
from .ignore_patterns import IgnorePatterns
from .ast_simhash_detector import ASTSimHashDetector
from .trivial_filter import TrivialPatternFilter, TrivialFilterConfig
from .semantic_detector import SemanticAwareDuplicateDetector


def setup_logging(level: str = "INFO"):
    """Set up logging configuration."""
    # Create a custom formatter that shortens module names
    class ShortNameFormatter(logging.Formatter):
        def format(self, record):
            # Shorten the logger name to just the last component
            parts = record.name.split('.')
            if len(parts) > 1:
                record.short_name = parts[-1]
            else:
                record.short_name = record.name
            return super().format(record)
    
    # Configure root logger
    handler = logging.StreamHandler()
    
    # Only show timestamps and messages for INFO level, more detail for DEBUG
    if level.upper() == "INFO":
        # Simplified format for INFO level
        formatter = ShortNameFormatter('%(message)s')
    else:
        # More detailed format for DEBUG level
        formatter = ShortNameFormatter('%(asctime)s - %(short_name)s - %(levelname)s - %(message)s')
    
    handler.setFormatter(formatter)
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.handlers = []  # Clear existing handlers
    root_logger.addHandler(handler)
    
    # Suppress verbose logging from specific modules in INFO mode
    if level.upper() == "INFO":
        logging.getLogger('oopstracker.ast_simhash_detector').setLevel(logging.WARNING)
        logging.getLogger('oopstracker.ast_database').setLevel(logging.WARNING)
        logging.getLogger('oopstracker.ignore_patterns').setLevel(logging.WARNING)


# format_file_size関数は util/format_utils.py に移動されました
# 新しいimport文を追加してください: from util.format_utils import format_file_size



async def async_main():
    """Async main function."""
    return await _main_impl()

def main():
    """Main CLI entry point."""
    try:
        return asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\n🚫 Interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

async def _main_impl():
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
        "--semantic-analysis", "--semantic",
        action="store_true",
        help="Enable semantic duplicate analysis using LLM (requires intent_unified)"
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
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Check command (main functionality - unified scan + detect)
    check_parser = subparsers.add_parser("check", help="Scan directory and find meaningful code duplicates")
    check_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory or file to check (default: current directory)"
    )
    check_parser.add_argument(
        "--pattern", "-p",
        default="*.py",
        help="File pattern to match (default: *.py)"
    )
    check_parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-scan all files (ignore cache)"
    )
    check_parser.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Don't respect .gitignore files"
    )
    check_parser.add_argument(
        "--show-all",
        action="store_true",
        help="Legacy option (duplicates now shown by default)"
    )
    check_parser.add_argument(
        "--duplicates-only",
        action="store_true",
        help="Only show duplicates analysis (skip file scanning)"
    )
    check_parser.add_argument(
        "--threshold",
        type=float,
        help="Similarity threshold for duplicates (default: uses global setting)"
    )
    check_parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of duplicate pairs to show (default: 50)"
    )
    check_parser.add_argument(
        "--fast",
        action="store_true",
        default=True,
        help="Use fast SimHash pre-filtering (default: True)"
    )
    check_parser.add_argument(
        "--exhaustive",
        action="store_true",
        help="Use exhaustive O(n²) search for maximum accuracy"
    )
    check_parser.add_argument(
        "--include-trivial",
        action="store_true",
        help="Include trivial duplicates (pass classes, simple getters, etc.)"
    )
    check_parser.add_argument(
        "--semantic", "-s",
        action="store_true",
        default=True,
        help="Enable semantic analysis using LLM (default: True)"
    )
    check_parser.add_argument(
        "--no-semantic",
        action="store_true",
        help="Disable semantic analysis"
    )
    check_parser.add_argument(
        "--semantic-threshold",
        type=float,
        default=0.7,
        help="Semantic similarity threshold (default: 0.7)"
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
        choices=["table", "json", "detailed"],
        default="table",
        help="Output format (default: table)"
    )
    list_parser.add_argument(
        "--show-code", "-c",
        action="store_true",
        help="Show code snippets in output"
    )
    list_parser.add_argument(
        "--limit", "-l",
        type=int,
        help="Limit number of records to show"
    )
    list_parser.add_argument(
        "--sort-by", "-s",
        choices=["timestamp", "function", "file", "hash"],
        default="timestamp",
        help="Sort records by field (default: timestamp)"
    )
    
    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear all registered code")
    clear_parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    # AST analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze code structure (AST mode only)")
    analyze_parser.add_argument(
        "code",
        help="Code to analyze"
    )
    analyze_parser.add_argument(
        "--file-path", "-F",
        help="File path for context"
    )
    
    
    # Relations command
    relations_parser = subparsers.add_parser("relations", help="Show relationships between code units")
    relations_parser.add_argument(
        "--hash", 
        help="Code hash to find relations for (if not provided, shows overall graph stats)"
    )
    relations_parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.3,
        help="Similarity threshold for connections (default: 0.3)"
    )
    relations_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="Maximum number of related items to show (default: 10)"
    )
    relations_parser.add_argument(
        "--graph",
        action="store_true",
        help="Show graph structure instead of specific relations"
    )
    relations_parser.add_argument(
        "--fast",
        action="store_true",
        default=True,
        help="Use fast SimHash filtering (default: True)"
    )
    relations_parser.add_argument(
        "--full",
        action="store_true",
        help="Use full O(n²) computation for maximum accuracy"
    )
    relations_parser.add_argument(
        "--auto",
        action="store_true",
        default=True,
        help="Automatically find optimal threshold using adaptive search (default: True)"
    )
    relations_parser.add_argument(
        "--manual",
        action="store_true",
        help="Use manual threshold instead of automatic search"
    )
    relations_parser.add_argument(
        "--target",
        type=int,
        default=200,
        help="Target number of connections for auto mode (default: 200)"
    )
    relations_parser.add_argument(
        "--max-connections",
        type=int,
        default=1000,
        help="Maximum connections before stopping in auto mode (default: 1000)"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    # Initialize AST detector
    try:
        detector = ASTSimHashDetector(hamming_threshold=args.hamming_threshold)
        # Only show initialization message in verbose mode
        if args.log_level == "DEBUG":
            print(f"🧠 AST-based structural analysis (hamming threshold: {args.hamming_threshold})")
    except Exception as e:
        print(f"❌ Failed to initialize OOPStracker: {e}")
        sys.exit(1)
    
    # Initialize semantic detector based on command and options
    semantic_detector = None
    
    # For check command, use semantic analysis by default unless --no-semantic is specified
    if args.command == "check":
        if not args.no_semantic:
            # Override global semantic_analysis setting for check command
            args.semantic_analysis = True
            # Use check command's semantic threshold if specified
            if hasattr(args, 'semantic_threshold') and args.semantic_threshold:
                args.semantic_threshold = args.semantic_threshold
        else:
            args.semantic_analysis = False
    
    # Initialize semantic detector if enabled
    if hasattr(args, 'semantic_analysis') and args.semantic_analysis:
        try:
            semantic_detector = SemanticAwareDuplicateDetector(intent_unified_available=True)
            await semantic_detector.initialize()
            print("🧠 Semantic analysis enabled (LLM-based)")
        except Exception as e:
            print(f"⚠️  Failed to initialize semantic analysis: {e}")
            print("🔄 Falling back to structural analysis only")
            semantic_detector = SemanticAwareDuplicateDetector(intent_unified_available=False)
            await semantic_detector.initialize()
    
    # Handle commands
    try:
        if args.command == "check":
            # If duplicates-only mode, skip file scanning
            if args.duplicates_only:
                print("🔍 Finding potential duplicates...")
                threshold = args.threshold if args.threshold else args.similarity_threshold
                use_fast_mode = not args.exhaustive
                pairs = detector.find_potential_duplicates(threshold=threshold, use_fast_mode=use_fast_mode, include_trivial=args.include_trivial)
                
                if not pairs:
                    print("✅ No duplicates found")
                else:
                    print(f"⚠️  Found {len(pairs)} potential duplicate pairs (threshold: {threshold}):")
                    
                    for i, (unit1, unit2, similarity) in enumerate(pairs[:args.limit], 1):
                        print(f"\n {i}. Similarity: {similarity:.3f}")
                        type1 = unit1.metadata.get('type', 'unknown') if unit1.metadata else 'unknown'
                        type2 = unit2.metadata.get('type', 'unknown') if unit2.metadata else 'unknown'
                        
                        # Get line information from CodeUnit if available
                        unit1_code_unit = detector.code_units.get(unit1.code_hash)
                        unit2_code_unit = detector.code_units.get(unit2.code_hash)
                        
                        line1 = f":{unit1_code_unit.start_line}" if unit1_code_unit and unit1_code_unit.start_line else ""
                        line2 = f":{unit2_code_unit.start_line}" if unit2_code_unit and unit2_code_unit.start_line else ""
                        
                        print(f"    {type1}: {unit1.function_name or 'N/A'} in {unit1.file_path or 'N/A'}{line1}")
                        print(f"    {type2}: {unit2.function_name or 'N/A'} in {unit2.file_path or 'N/A'}{line2}")
                return
            
            # Unified check command: scan changed files and detect duplicates
            path = Path(args.path)
            
            print(f"🔍 Checking {path} for updates and duplicates...")
            
            # Initialize ignore patterns
            ignore_patterns = IgnorePatterns(
                project_root=str(path if path.is_dir() else path.parent),
                use_gitignore=not args.no_gitignore
            )
            
            # Collect files to check
            if path.is_file():
                all_files = [str(path)] if not ignore_patterns.should_ignore(path) else []
            else:
                all_files = []
                for file_path in path.rglob(args.pattern):
                    if file_path.is_file() and not ignore_patterns.should_ignore(file_path):
                        all_files.append(str(file_path))
            
            print(f"📁 Found {len(all_files)} Python files")
            
            # Check for deleted files
            current_files_set = set(all_files)
            deleted_files = detector.db_manager.check_and_mark_deleted_files(current_files_set)
            if deleted_files:
                print(f"🗑️  {len(deleted_files)} tracked files no longer exist (excluded from duplicate detection)")
            
            # Filter to only changed files unless forced
            if args.force:
                files_to_scan = all_files
                print(f"🔄 Force mode: scanning all {len(files_to_scan)} files")
            else:
                changed_files = detector.db_manager.get_changed_files(all_files)
                files_to_scan = changed_files
                print(f"📝 {len(changed_files)} files have changed since last scan")
            
            # Scan changed files
            new_records = []
            updated_files = 0
            duplicates_found = []
            
            # Show progress if there are many files
            if len(files_to_scan) > 10:
                print(f"⏳ Scanning {len(files_to_scan)} files...")
            
            for i, file_path in enumerate(files_to_scan):
                # Show progress for large scans
                if len(files_to_scan) > 50 and (i + 1) % 50 == 0:
                    print(f"   Progress: {i + 1}/{len(files_to_scan)} files...")
                
                records = detector.register_file(file_path, force=args.force)
                if records:
                    new_records.extend(records)
                    updated_files += 1
                    
                    # Check for duplicates in newly registered code
                    for record in records:
                        if record.metadata and record.metadata.get('type') == 'module':
                            continue
                        
                        result = detector.find_similar(
                            record.code_content, 
                            record.function_name, 
                            file_path
                        )
                        
                        if result.is_duplicate and result.matched_records:
                            # Collect duplicate info for summary
                            dup_info = {
                                'type': record.metadata.get('type', 'unknown') if record.metadata else 'unknown',
                                'name': record.function_name,
                                'file': file_path,
                                'matches': []
                            }
                            
                            for matched in result.matched_records[:3]:
                                # Skip if it's the same record we just added
                                if matched.code_hash == record.code_hash:
                                    continue
                                    
                                dup_info['matches'].append({
                                    'name': matched.function_name or 'N/A',
                                    'file': matched.file_path or 'N/A',
                                    'similarity': matched.similarity_score or 0
                                })
                            
                            if dup_info['matches']:
                                duplicates_found.append(dup_info)
            
            # Summary
            print(f"\n📊 Summary:")
            print(f"   Files scanned: {updated_files}")
            print(f"   New/updated code units: {len(new_records)}")
            
            # Show duplicates if found
            if duplicates_found:
                print(f"\n⚠️  Found {len(duplicates_found)} duplicates:")
                for dup in duplicates_found[:10]:  # Show first 10
                    print(f"\n   {dup['type']}: '{dup['name']}' in {dup['file']}")
                    for match in dup['matches'][:2]:  # Show first 2 matches
                        print(f"      Similar to: {match['name']} in {match['file']} (similarity: {match['similarity']:.3f})")
                
                if len(duplicates_found) > 10:
                    print(f"\n   ... and {len(duplicates_found) - 10} more duplicates")
            
            # Always show project-wide duplicates by default
            print(f"\n🔍 Checking all duplicates in project...")
            use_fast_mode = not args.exhaustive
            threshold = 0.7  # More practical threshold for meaningful duplicates
            duplicates = detector.find_potential_duplicates(threshold=threshold, use_fast_mode=use_fast_mode, include_trivial=args.include_trivial)
            
            if duplicates:
                print(f"\n⚠️  Found {len(duplicates)} potential duplicate pairs (threshold: {threshold}):")
                display_limit = 15  # Show more duplicates by default
                for i, (record1, record2, similarity) in enumerate(duplicates[:display_limit], 1):
                    type1 = record1.metadata.get('type', 'unknown') if record1.metadata else 'unknown'
                    type2 = record2.metadata.get('type', 'unknown') if record2.metadata else 'unknown'
                    
                    # Get line information from CodeUnit if available
                    unit1 = detector.code_units.get(record1.code_hash)
                    unit2 = detector.code_units.get(record2.code_hash)
                    
                    line1 = f":{unit1.start_line}" if unit1 and unit1.start_line else ""
                    line2 = f":{unit2.start_line}" if unit2 and unit2.start_line else ""
                    
                    print(f"\n{i:2d}. Similarity: {similarity:.3f}")
                    print(f"    {type1}: {record1.function_name or 'N/A'} in {record1.file_path or 'N/A'}{line1}")
                    print(f"    {type2}: {record2.function_name or 'N/A'} in {record2.file_path or 'N/A'}{line2}")
                
                if len(duplicates) > display_limit:
                    print(f"\n... and {len(duplicates) - display_limit} more pairs")
                
                # Show helpful tips
                if not args.include_trivial:
                    print(f"\n💡 Use --include-trivial to see all duplicates (including simple classes)")
                print(f"💡 Use --threshold X to adjust sensitivity (current: {threshold})")
                print(f"💡 Use --exhaustive for higher accuracy (slower)")
            else:
                print(f"\n✅ No meaningful duplicates found at threshold {threshold}!")
                print(f"💡 Try --include-trivial or lower --threshold for more results")
            
            # Semantic analysis if enabled
            if semantic_detector and hasattr(args, 'semantic_analysis') and args.semantic_analysis:
                print(f"\n🧠 Performing semantic analysis...")
                try:
                    # Convert structural duplicates to CodeRecords for semantic analysis
                    code_records = []
                    for record1, record2, similarity in duplicates[:10]:  # Limit to top 10 for semantic analysis
                        code_records.extend([record1, record2])
                    
                    # Remove duplicates from code_records
                    unique_records = []
                    seen_hashes = set()
                    for record in code_records:
                        if record.code_hash not in seen_hashes:
                            unique_records.append(record)
                            seen_hashes.add(record.code_hash)
                    
                    if unique_records:
                        semantic_results = await semantic_detector.detect_duplicates(
                            code_records=unique_records,
                            enable_semantic=True,
                            semantic_threshold=args.semantic_threshold,
                            max_concurrent=args.max_semantic_concurrent
                        )
                        
                        semantic_duplicates = semantic_results.get('semantic_duplicates', [])
                        if semantic_duplicates:
                            print(f"\n🔍 Semantic analysis found {len(semantic_duplicates)} meaningful duplicates:")
                            for i, sem_dup in enumerate(semantic_duplicates[:5], 1):
                                print(f"\n{i:2d}. Semantic similarity: {sem_dup.semantic_similarity:.3f} (confidence: {sem_dup.confidence:.3f})")
                                print(f"    Method: {sem_dup.analysis_method}")
                                print(f"    {sem_dup.code_record_1.function_name or 'N/A'} in {sem_dup.code_record_1.file_path or 'N/A'}")
                                print(f"    {sem_dup.code_record_2.function_name or 'N/A'} in {sem_dup.code_record_2.file_path or 'N/A'}")
                                print(f"    Reasoning: {sem_dup.reasoning[:100]}...")
                            
                            if len(semantic_duplicates) > 5:
                                print(f"\n... and {len(semantic_duplicates) - 5} more semantic duplicates")
                        else:
                            print(f"\n✅ No semantic duplicates found above threshold {args.semantic_threshold}")
                        
                        # Show analysis summary
                        summary = semantic_results.get('summary', {})
                        if summary:
                            print(f"\n📊 Semantic Analysis Summary:")
                            print(f"   Total records analyzed: {summary.get('total_code_records', 0)}")
                            print(f"   Semantic analyses attempted: {summary.get('semantic_analysis_attempted', 0)}")
                            print(f"   Successful analyses: {summary.get('semantic_analysis_successful', 0)}")
                            print(f"   Failed analyses: {summary.get('semantic_analysis_failed', 0)}")
                            print(f"   Recommendation: {summary.get('recommendation', 'N/A')}")
                    else:
                        print(f"\n📝 No structural duplicates available for semantic analysis")
                        
                except Exception as e:
                    print(f"\n❌ Semantic analysis failed: {e}")
                    if args.log_level == "DEBUG":
                        import traceback
                        traceback.print_exc()
                
        elif args.command == "register":
            records = detector.register_code(
                args.code,
                function_name=args.function_name,
                file_path=args.file_path
            )
            if records:
                print(f"✅ Registered {len(records)} code units")
                for record in records:
                    unit_type = record.metadata.get('type', 'unknown') if record.metadata else 'unknown'
                    print(f"   {unit_type}: {record.function_name or 'N/A'} (hash: {record.code_hash[:16]}...)")
            else:
                print("⚠️  No code units found to register")
            
        elif args.command == "list":
            records = detector.get_all_records()
            
            # Sort records
            if args.sort_by == "timestamp":
                records.sort(key=lambda r: r.timestamp, reverse=True)
            elif args.sort_by == "function":
                records.sort(key=lambda r: r.function_name or "")
            elif args.sort_by == "file":
                records.sort(key=lambda r: r.file_path or "")
            elif args.sort_by == "hash":
                records.sort(key=lambda r: r.code_hash)
            
            # Apply limit
            if args.limit:
                records = records[:args.limit]
            
            if args.format == "json":
                output = [record.to_dict() for record in records]
                print(json.dumps(output, indent=2, default=str))
            elif args.format == "detailed":
                print(f"\n📊 Code Records Summary:")
                print(f"   Total records: {len(detector.get_all_records())}")
                if args.limit:
                    print(f"   Showing: {len(records)} records")
                print(f"   Sorted by: {args.sort_by}")
                print("\n" + "=" * 80)
                
                for i, record in enumerate(records, 1):
                    print(f"\n📝 Record #{i}")
                    print(f"   🔍 Hash: {record.code_hash}")
                    print(f"   🏷️  Function: {record.function_name or 'N/A'}")
                    print(f"   📁 File: {record.file_path or 'N/A'}")
                    print(f"   ⏰ Timestamp: {record.timestamp}")
                    if record.metadata:
                        print(f"   📋 Metadata: {record.metadata}")
                    
                    if args.show_code:
                        print(f"   💻 Code:")
                        code_lines = record.code_content.strip().split('\n')
                        for j, line in enumerate(code_lines[:10], 1):  # Show first 10 lines
                            print(f"      {j:2d}| {line}")
                        if len(code_lines) > 10:
                            print(f"         ... ({len(code_lines) - 10} more lines)")
                    
                    print("   " + "-" * 70)
            else:  # table format
                print(f"\n📋 Found {len(records)} code records (sorted by {args.sort_by}):")
                all_records = detector.get_all_records()
                if len(all_records) != len(records) and args.limit:
                    print(f"   (Showing {len(records)} of {len(all_records)} total records)")
                print()
                
                # Table header
                print(f"{'#':>3} {'Function':20} {'File':25} {'Hash':16} {'Timestamp':19}")
                print("-" * 85)
                
                for i, record in enumerate(records, 1):
                    func_name = (record.function_name or 'N/A')[:19]
                    file_name = (record.file_path or 'N/A')[:24]
                    hash_short = record.code_hash[:16]
                    timestamp = str(record.timestamp)[:19]
                    
                    print(f"{i:3d} {func_name:20} {file_name:25} {hash_short:16} {timestamp:19}")
                    
                    if args.show_code:
                        preview = record.code_content.strip()[:60].replace('\n', '\\n')
                        print(f"    Code preview: {preview}...")
                        
                        # Show unit type for AST mode
                        if record.metadata and 'type' in record.metadata:
                            unit_type = record.metadata['type']
                            complexity = record.metadata.get('complexity', 0)
                            print(f"    Type: {unit_type}, Complexity: {complexity}")
                        
                        print()
                    
        elif args.command == "clear":
            if not args.yes:
                confirm = input("Are you sure you want to clear all registered code? (y/N): ")
                if confirm.lower() != 'y':
                    print("Operation cancelled")
                    sys.exit(0)
            
            detector.clear_memory()
            print("✅ Memory cleared successfully")
            
        elif args.command == "analyze":
            analysis = detector.analyze_code_structure(args.code, args.file_path)
            
            print(f"\n📊 Code Structure Analysis:")
            print(f"   Total units: {analysis['total_units']}")
            print(f"   Functions: {len(analysis['functions'])}")
            print(f"   Classes: {len(analysis['classes'])}")
            print(f"   Total complexity: {analysis['total_complexity']}")
            print(f"   Average complexity: {analysis['average_complexity']:.2f}")
            print(f"   Dependencies: {', '.join(analysis['dependencies']) if analysis['dependencies'] else 'None'}")
            
            if analysis['functions']:
                print(f"\n🔄 Functions:")
                for func in analysis['functions']:
                    print(f"   • {func.name} (lines {func.start_line}-{func.end_line}, complexity: {func.complexity_score})")
            
            if analysis['classes']:
                print(f"\n🏷️ Classes:")
                for cls in analysis['classes']:
                    print(f"   • {cls.name} (lines {cls.start_line}-{cls.end_line}, complexity: {cls.complexity_score})")
            
        elif args.command == "relations":
            # Use auto mode by default unless manual is specified
            use_auto = not args.manual
            
            if use_auto:
                # Adaptive threshold search mode
                print(f"🔍 Auto-finding optimal threshold (target: {args.target} connections, max: {args.max_connections})...")
                
                results = detector.find_relations_adaptive(
                    target_connections=args.target,
                    max_connections=args.max_connections
                )
                
                # Display results
                print(f"\n🎯 Adaptive Search Results:")
                print(f"   Final threshold: {results['threshold']:.2f}")
                print(f"   Final connections: {results['connections']}")
                print(f"   Stop reason: {results['stop_reason']}")
                print(f"   Iterations: {len(results['iterations'])}")
                
                # Show iteration history
                if len(results['iterations']) > 1:
                    print(f"\n📊 Search History:")
                    for i, iteration in enumerate(results['iterations'][-5:], max(1, len(results['iterations'])-4)):
                        print(f"   {i:2d}. threshold={iteration['threshold']:.2f} → {iteration['estimated_connections']} connections ({iteration['time']:.2f}s)")
                
                # Display the final graph
                graph = results['final_graph']
                total_nodes = len(graph)
                connected_nodes = sum(1 for connections in graph.values() if connections)
                
                print(f"\n🕸️  Final Similarity Graph:")
                print(f"   Total nodes: {total_nodes}")
                print(f"   Connected nodes: {connected_nodes}")
                print(f"   Total connections: {results['connections']}")
                
                if connected_nodes > 0:
                    avg_connections = results['connections'] * 2 / total_nodes
                    print(f"   Average connections per node: {avg_connections:.2f}")
                    
                    # Show top connected nodes
                    print(f"\n🔗 Top connected nodes (showing {min(10, connected_nodes)}):")
                    
                    node_connections = [(hash_code, len(connections)) for hash_code, connections in graph.items() if connections]
                    node_connections.sort(key=lambda x: x[1], reverse=True)
                    
                    for i, (hash_code, conn_count) in enumerate(node_connections[:10], 1):
                        record = detector.records.get(hash_code)
                        if record:
                            func_name = record.function_name or 'N/A'
                            file_path = record.file_path or 'N/A'
                            
                            # Get line information from CodeUnit if available
                            unit = detector.code_units.get(hash_code)
                            line_info = f":{unit.start_line}" if unit and unit.start_line else ""
                            
                            print(f"   {i:2d}. {func_name} ({file_path}{line_info}) - {conn_count} connections")
                            
                else:
                    print(f"   No connections found")
                
            else:
                # Determine computation mode
                use_fast_mode = not args.full
                mode_name = "FAST" if use_fast_mode else "FULL"
                
                if args.graph:
                    # Show overall graph structure
                    print(f"🔄 Building similarity graph ({mode_name} mode)...")
                    graph = detector.build_similarity_graph(args.threshold, use_fast_mode)
                    
                    print(f"\n🕸️  Similarity Graph (threshold: {args.threshold}):")
                    
                    # Calculate graph statistics
                    total_nodes = len(graph)
                    connected_nodes = sum(1 for connections in graph.values() if connections)
                    total_connections = sum(len(connections) for connections in graph.values()) // 2
                    avg_connections = total_connections * 2 / total_nodes if total_nodes > 0 else 0
                    
                    print(f"   Total nodes: {total_nodes}")
                    print(f"   Connected nodes: {connected_nodes}")
                    print(f"   Total connections: {total_connections}")
                    print(f"   Average connections per node: {avg_connections:.2f}")
                    
                    # Provide guidance based on results
                    if total_connections > 100000:
                        print(f"\n💡 Too many connections! Try higher threshold:")
                        print(f"   --threshold 0.7  (for similar functions)")
                        print(f"   --threshold 0.8  (for near-duplicates)")
                    elif total_connections < 10:
                        print(f"\n💡 Very few connections. Try lower threshold:")
                        print(f"   --threshold 0.2  (for loose similarities)")
                        print(f"   --threshold 0.1  (for any structural resemblance)")
                    else:
                        print(f"\n✅ Good threshold level for analysis")
                    
                    if args.limit and connected_nodes > 0:
                        print(f"\n🔗 Top connected nodes (showing {min(args.limit, connected_nodes)}):")
                        
                        # Sort nodes by number of connections
                        node_connections = [(hash_code, len(connections)) for hash_code, connections in graph.items() if connections]
                        node_connections.sort(key=lambda x: x[1], reverse=True)
                        
                        for i, (hash_code, conn_count) in enumerate(node_connections[:args.limit], 1):
                            record = detector.records.get(hash_code)
                            if record:
                                func_name = record.function_name or 'N/A'
                                file_path = record.file_path or 'N/A'
                                
                                # Get line information from CodeUnit if available
                                unit = detector.code_units.get(hash_code)
                                line_info = f":{unit.start_line}" if unit and unit.start_line else ""
                                
                                print(f"   {i:2d}. {func_name} ({file_path}{line_info}) - {conn_count} connections")
                
                elif args.hash:
                    # Show relations for specific code unit
                    related = detector.get_related_units(args.hash, args.threshold, args.limit)
                    
                    if not related:
                        print(f"❌ No related units found for hash {args.hash[:16]}... (threshold: {args.threshold})")
                    else:
                        target_record = detector.records.get(args.hash)
                        if target_record:
                            print(f"\n🔗 Related to: {target_record.function_name or 'N/A'} in {target_record.file_path or 'N/A'}")
                        else:
                            print(f"\n🔗 Related to hash: {args.hash[:16]}...")
                        
                        print(f"   Found {len(related)} related units (threshold: {args.threshold}):\n")
                        
                        for i, (record, similarity) in enumerate(related, 1):
                            unit_type = record.metadata.get('type', 'unknown') if record.metadata else 'unknown'
                            func_name = record.function_name or 'N/A'
                            file_path = record.file_path or 'N/A'
                            
                            # Get line information from CodeUnit if available
                            unit = detector.code_units.get(record.code_hash)
                            line_info = f":{unit.start_line}" if unit and unit.start_line else ""
                            
                            print(f"   {i:2d}. {unit_type}: {func_name} in {file_path}{line_info}")
                            print(f"       Similarity: {similarity:.3f}")
                            print(f"       Hash: {record.code_hash[:16]}...")
                            print()
                
                else:
                    # Interactive mode - show top connected units and let user pick
                    print(f"🔄 Building similarity graph ({mode_name} mode)...")
                    graph = detector.build_similarity_graph(args.threshold, use_fast_mode)
                    
                    if not any(connections for connections in graph.values()):
                        print(f"❌ No connections found with threshold {args.threshold}")
                        print("   Try lowering the threshold with --threshold 0.2")
                    else:
                        print(f"\n🕸️  Similarity Graph Overview (threshold: {args.threshold}):")
                        
                        # Show top connected units
                        node_connections = [(hash_code, len(connections)) for hash_code, connections in graph.items() if connections]
                        node_connections.sort(key=lambda x: x[1], reverse=True)
                        
                        print(f"   Top {min(10, len(node_connections))} most connected units:\n")
                        
                        for i, (hash_code, conn_count) in enumerate(node_connections[:10], 1):
                            record = detector.records.get(hash_code)
                            if record:
                                unit_type = record.metadata.get('type', 'unknown') if record.metadata else 'unknown'
                                func_name = record.function_name or 'N/A'
                                file_path = record.file_path or 'N/A'
                                
                                # Get line information from CodeUnit if available
                                unit = detector.code_units.get(hash_code)
                                line_info = f":{unit.start_line}" if unit and unit.start_line else ""
                                
                                print(f"   {i:2d}. {unit_type}: {func_name} ({file_path}{line_info})")
                                print(f"       {conn_count} connections | Hash: {record.code_hash[:16]}...")
                                print()
                        
                        print(f"💡 Use --hash <code_hash> to see specific relations")
                        print(f"💡 Use --graph to see full graph statistics")
                        print(f"💡 Try different thresholds:")
                        print(f"   0.8+ = Near duplicates")
                        print(f"   0.6+ = Similar functions") 
                        print(f"   0.4+ = Related patterns")
                        print(f"   0.2+ = Loose similarities")
            
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
    finally:
        # Cleanup semantic detector if initialized
        if semantic_detector:
            try:
                await semantic_detector.cleanup()
            except Exception as e:
                if args.log_level == "DEBUG":
                    print(f"⚠️  Semantic detector cleanup failed: {e}")


if __name__ == "__main__":
    main()