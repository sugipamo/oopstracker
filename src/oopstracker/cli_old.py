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


def setup_logging(level: str = "WARNING"):
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
    
    # Suppress verbose logging from specific modules
    if level.upper() in ["INFO", "WARNING"]:
        logging.getLogger('oopstracker.ast_simhash_detector').setLevel(logging.WARNING)
        logging.getLogger('oopstracker.ast_database').setLevel(logging.WARNING)
        logging.getLogger('oopstracker.ignore_patterns').setLevel(logging.WARNING)
        logging.getLogger('oopstracker.intent_tree_fixed_adapter').setLevel(logging.WARNING)
        logging.getLogger('oopstracker.intent_tree_adapter').setLevel(logging.WARNING)
        # Suppress external library logs
        logging.getLogger('intent_unified').setLevel(logging.WARNING)
        logging.getLogger('llm_providers').setLevel(logging.WARNING)
        logging.getLogger('aiohttp').setLevel(logging.WARNING)
        logging.getLogger('intent_tree').setLevel(logging.WARNING)
        logging.getLogger('intent_tree.core').setLevel(logging.WARNING)
        logging.getLogger('intent_tree.data').setLevel(logging.WARNING)


# format_file_size関数は util/format_utils.py に移動されました
# 新しいimport文を追加してください: from util.format_utils import format_file_size

@contextlib.contextmanager
def suppress_unwanted_output():
    """Context manager to suppress unwanted stdout messages from external libraries."""
    import sys
    from io import StringIO
    
    class FilteredStdout:
        def __init__(self, original_stdout):
            self.original_stdout = original_stdout
            self.buffer = StringIO()
            
        def write(self, text):
            # Filter out unwanted messages
            unwanted_patterns = [
                "Session",
                "is not active",
                "status: completed",
                "warning: `VIRTUAL_ENV=",
                "does not match the project environment path"
            ]
            
            if not any(pattern in text for pattern in unwanted_patterns):
                self.original_stdout.write(text)
            else:
                # Suppress the unwanted message
                pass
                
        def flush(self):
            self.original_stdout.flush()
            
        def __getattr__(self, name):
            return getattr(self.original_stdout, name)
    
    original_stdout = sys.stdout
    try:
        sys.stdout = FilteredStdout(original_stdout)
        yield
    finally:
        sys.stdout = original_stdout



def format_duplicate_pair(detector, record1: CodeRecord, record2: CodeRecord, similarity: float, index: int) -> str:
    """Format a duplicate pair for display with consistent line number information."""
    type1 = record1.metadata.get('type', 'unknown') if record1.metadata else 'unknown'
    type2 = record2.metadata.get('type', 'unknown') if record2.metadata else 'unknown'
    
    # Get line information from CodeUnit if available
    unit1 = detector.code_units.get(record1.code_hash)
    unit2 = detector.code_units.get(record2.code_hash)
    
    line1 = f":{unit1.start_line}" if unit1 and unit1.start_line else ""
    line2 = f":{unit2.start_line}" if unit2 and unit2.start_line else ""
    
    output = f"\n{index:2d}. Similarity: {similarity:.3f}\n"
    output += f"    {type1}: {record1.function_name or 'N/A'} in {record1.file_path or 'N/A'}{line1}\n"
    output += f"    {type2}: {record2.function_name or 'N/A'} in {record2.file_path or 'N/A'}{line2}"
    
    return output


def format_semantic_duplicate(detector, sem_dup, index: int) -> str:
    """Format a semantic duplicate for display with consistent line number information."""
    record1 = sem_dup.code_record_1
    record2 = sem_dup.code_record_2
    
    # Get line information from CodeUnit if available (same logic as format_duplicate_pair)
    unit1 = detector.code_units.get(record1.code_hash)
    unit2 = detector.code_units.get(record2.code_hash)
    
    line1 = f":{unit1.start_line}" if unit1 and unit1.start_line else ""
    line2 = f":{unit2.start_line}" if unit2 and unit2.start_line else ""
    
    output = f"\n{index:2d}. Semantic similarity: {sem_dup.semantic_similarity:.3f} (confidence: {sem_dup.confidence:.3f})\n"
    output += f"    Method: {sem_dup.analysis_method}\n"
    output += f"    {record1.function_name or 'N/A'} in {record1.file_path or 'N/A'}{line1}\n"
    output += f"    {record2.function_name or 'N/A'} in {record2.file_path or 'N/A'}{line2}\n"
    output += f"    Reasoning: {sem_dup.reasoning[:100]}..."
    
    return output


async def async_main():
    """Async main function."""
    return await _main_impl()

def main():
    """Main CLI entry point."""
    try:
        with suppress_unwanted_output():
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
    
    # Check command - simplified with smart defaults
    check_parser = subparsers.add_parser("check", help="Analyze code structure and function groups")
    check_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory or file to analyze (default: current directory)"
    )
    check_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed analysis for each function group"
    )
    check_parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Show only summary statistics"
    )
    check_parser.add_argument(
        "--no-clustering",
        action="store_true",
        help="Disable automatic function grouping"
    )
    check_parser.add_argument(
        "--enable-duplicate-detection",
        action="store_true",
        help="Enable duplicate detection (disabled by default)"
    )
    check_parser.add_argument(
        "--disable-duplicate-detection",
        action="store_true",
        help="Disable duplicate detection"
    )
    check_parser.add_argument(
        "--classification-only",
        action="store_true",
        help="Only run classification, skip duplicate detection"
    )
    
    # Advanced options (hidden from main flow)
    advanced_group = check_parser.add_argument_group('advanced options')
    advanced_group.add_argument(
        "--pattern", "-p",
        default="*.py",
        help="File pattern to match (default: *.py)"
    )
    advanced_group.add_argument(
        "--force",
        action="store_true",
        help="Force re-scan all files"
    )
    advanced_group.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Don't respect .gitignore files"
    )
    advanced_group.add_argument(
        "--include-tests",
        action="store_true",
        help="Include test files in analysis"
    )
    
    # Legacy duplicate detection (special case only)
    legacy_group = check_parser.add_argument_group('legacy duplicate detection')
    legacy_group.add_argument(
        "--duplicates",
        action="store_true",
        help="Enable legacy duplicate detection mode"
    )
    legacy_group.add_argument(
        "--duplicates-threshold",
        type=float,
        default=0.8,
        help="Similarity threshold for duplicates (default: 0.8)"
    )
    legacy_group.add_argument(
        "--duplicates-only",
        action="store_true",
        help="Only show duplicates, skip file scanning"
    )
    legacy_group.add_argument(
        "--exhaustive",
        action="store_true",
        help="Use exhaustive mode for higher accuracy (slower)"
    )
    legacy_group.add_argument(
        "--top-percent",
        type=float,
        help="Show top X percent of duplicates (dynamic threshold)"
    )
    legacy_group.add_argument(
        "--include-trivial",
        action="store_true",
        help="Include trivial duplicates (simple classes, etc.)"
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
    
    # Akinator command - Interactive code exploration
    akinator_parser = subparsers.add_parser("akinator", help="Interactive code exploration using Akinator-style questions")
    akinator_parser.add_argument(
        "code",
        help="Code snippet to find similar code for"
    )
    akinator_parser.add_argument(
        "--max-questions",
        type=int,
        default=10,
        help="Maximum number of questions to ask (default: 10)"
    )
    akinator_parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout for each question in seconds (default: 30)"
    )
    akinator_parser.add_argument(
        "--auto-answer",
        action="store_true",
        help="Auto-answer questions using regex matching (for testing)"
    )
    akinator_parser.add_argument(
        "--show-learning",
        action="store_true",
        help="Show learning statistics and feature effectiveness"
    )
    
    # Add relations arguments separately
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
        detector = ASTSimHashDetector(
            hamming_threshold=args.hamming_threshold,
            include_tests=getattr(args, 'include_tests', False)
        )
        # Only show initialization message in verbose mode
        if args.log_level == "DEBUG":
            print(f"🧠 AST-based structural analysis (hamming threshold: {args.hamming_threshold})")
    except Exception as e:
        print(f"❌ Failed to initialize OOPStracker: {e}")
        return 1
    
    # Initialize semantic detector based on command and options
    semantic_detector = None
    
    # For check command, semantic analysis is built-in to clustering
    if args.command == "check":
        # Semantic analysis is now integrated into the clustering system
        args.semantic_analysis = True
    
    # For akinator command, always enable semantic analysis
    if args.command == "akinator":
        args.semantic_analysis = True
    
    # Initialize semantic detector if enabled
    if hasattr(args, 'semantic_analysis') and args.semantic_analysis:
        try:
            semantic_detector = SemanticAwareDuplicateDetector(intent_unified_available=True, enable_intent_tree=True)
            await semantic_detector.initialize()
            print("🧠 Semantic analysis enabled (LLM-based)")
        except Exception as e:
            print(f"⚠️  Failed to initialize semantic analysis: {e}")
            print("🔄 Falling back to structural analysis only")
            semantic_detector = SemanticAwareDuplicateDetector(intent_unified_available=False, enable_intent_tree=True)
            await semantic_detector.initialize()
    
    # Create command context
    context = CommandContext(
        detector=detector,
        semantic_detector=semantic_detector,
        args=args
    )
    
    # Handle commands
    try:
        # Use command handler
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
        return 1
    finally:
        # Cleanup semantic detector if initialized
        if semantic_detector:
            try:
                await semantic_detector.cleanup()
            except Exception as e:
                if args.log_level == "DEBUG":
                    print(f"⚠️  Semantic detector cleanup failed: {e}")
                    default_top_percent = 3.0  # Default to top 3% of duplicates
                    pairs = detector.find_potential_duplicates(threshold=0.7, use_fast_mode=use_fast_mode, include_trivial=args.include_trivial, silent=False, top_percent=default_top_percent)
                    threshold_display = f"dynamic (top {default_top_percent}%)"
                else:
                    threshold = args.threshold if args.threshold else args.similarity_threshold
                    pairs = detector.find_potential_duplicates(threshold=threshold, use_fast_mode=use_fast_mode, include_trivial=args.include_trivial, silent=False, top_percent=args.top_percent)
                    threshold_display = f"dynamic (top {args.top_percent}%)"
                
                if not pairs:
                    print("✅ No duplicates found")
                else:
                    print(f"⚠️  Found {len(pairs)} potential duplicate pairs ({threshold_display}):")
                    
                    for i, (unit1, unit2, similarity) in enumerate(pairs[:args.limit], 1):
                        print(format_duplicate_pair(detector, unit1, unit2, similarity, i))
                return 0
            
            # Unified check command: scan changed files and detect duplicates
            path = Path(args.path)
            
            print(f"🔍 Checking {path} for updates and duplicates...")
            
            # Initialize ignore patterns
            ignore_patterns = IgnorePatterns(
                project_root=str(path if path.is_dir() else path.parent),
                use_gitignore=not args.no_gitignore,
                include_tests=args.include_tests
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
            
            # Progress tracking
            progress_reporter = ProgressReporter(
                interval_seconds=5.0,
                min_items_for_display=50,
                silent=False
            )
            
            for i, file_path in enumerate(files_to_scan):
                # Show progress for large scans
                progress_reporter.print_progress(i + 1, len(files_to_scan), unit="files")
                
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
            
            # Make duplicate detection optional - default OFF for focus on classification
            run_duplicate_detection = args.enable_duplicate_detection and not (args.classification_only or args.disable_duplicate_detection)
            
            if run_duplicate_detection:
                # Use dynamic threshold by default (top 3%) if not specified
                if args.top_percent is None:
                    default_top_percent = 3.0  # Default to top 3% of duplicates
                    duplicates = detector.find_potential_duplicates(threshold=0.7, use_fast_mode=use_fast_mode, include_trivial=args.include_trivial, silent=False, top_percent=default_top_percent)
                    threshold_display = f"dynamic (top {default_top_percent}%)"
                else:
                    threshold = 0.7  # More practical threshold for meaningful duplicates
                    duplicates = detector.find_potential_duplicates(threshold=threshold, use_fast_mode=use_fast_mode, include_trivial=args.include_trivial, silent=False, top_percent=args.top_percent)
                    threshold_display = f"dynamic (top {args.top_percent}%)"
            else:
                duplicates = []
                threshold_display = "disabled (focusing on classification)"
                print("🎯 Prioritizing function classification analysis")
            
            if duplicates:
                print(f"\n⚠️  Found {len(duplicates)} potential duplicate pairs ({threshold_display}):")
                display_limit = 15  # Show more duplicates by default
                for i, (record1, record2, similarity) in enumerate(duplicates[:display_limit], 1):
                    print(format_duplicate_pair(detector, record1, record2, similarity, i))
                
                if len(duplicates) > display_limit:
                    print(f"\n... and {len(duplicates) - display_limit} more pairs")
                
                # Show helpful tips
                if not args.include_trivial:
                    print(f"\n💡 Use --include-trivial to see all duplicates (including simple classes)")
                print(f"💡 Use --top-percent X to adjust sensitivity ({threshold_display})")
                print(f"💡 Use --exhaustive for higher accuracy (slower)")
            else:
                print(f"\n✅ No meaningful duplicates found ({threshold_display})!")
                print(f"💡 Try --include-trivial or lower --top-percent for more results")
            
            # Always run Function Classification System (default behavior)
            print(f"\n🎯 Function Classification Analysis")
            
            # Import here to avoid circular imports
            from .function_taxonomy_expert import FunctionTaxonomyExpert
            taxonomy_expert = FunctionTaxonomyExpert(enable_ai=True)
            
            # Get all functions from detector
            function_units = [unit for unit in detector.code_units.values() 
                            if unit.type == 'function']
            
            if function_units:
                total_functions = len(function_units)
                # Limit analysis for performance - analyze top 15 functions
                analysis_limit = min(15, total_functions)
                print(f"   Analyzing {analysis_limit} functions (of {total_functions} total)...")
                
                # Analyze functions in batches
                function_data = [(unit.source_code, unit.name) for unit in function_units[:analysis_limit]]
                classification_results = await taxonomy_expert.analyze_function_collection(function_data)
                
                # Display results
                category_counts = {}
                for i, result in enumerate(classification_results):
                    unit = function_units[i]
                    category = result.primary_category
                    category_counts[category] = category_counts.get(category, 0) + 1
                    
                    if hasattr(args, 'verbose') and args.verbose:
                        print(f"\n   📝 {unit.name} ({unit.file_path})")
                        print(f"      Category: {result.primary_category} (confidence: {result.confidence:.2f})")
                        print(f"      Methods: {', '.join(result.analysis_methods)}")
                        if result.alternative_categories:
                            alts = ', '.join([f"{cat}({conf:.2f})" for cat, conf in result.alternative_categories])
                            print(f"      Alternatives: {alts}")
                
                # Summary
                print(f"\n   📊 Classification Summary:")
                for category, count in sorted(category_counts.items()):
                    percentage = (count / len(classification_results)) * 100
                    print(f"      {category}: {count} functions ({percentage:.1f}%)")
                
                # Expert insights
                insights = taxonomy_expert.get_expert_insights()
                if 'performance_metrics' in insights:
                    print(f"      Average processing time: {insights['performance_metrics']['average_processing_time']:.3f}s")
                    
                if total_functions > analysis_limit:
                    print(f"      💡 Use --verbose to see detailed analysis of each function")
            else:
                print("   No functions found for classification")
            
            # Function Group Clustering Analysis (if enabled)
            if hasattr(args, 'enable_clustering') and args.enable_clustering:
                print(f"\n🔬 Function Group Clustering Analysis")
                
                # Import clustering system
                from .function_group_clustering import FunctionGroupClusteringSystem, ClusteringStrategy
                
                clustering_system = FunctionGroupClusteringSystem(enable_ai=True)
                
                # Load functions from detector
                all_functions = await clustering_system.load_all_functions_from_repository(list(detector.code_units.values()))
                
                if all_functions:
                    # Convert strategy string to enum
                    strategy_map = {
                        'category_based': ClusteringStrategy.CATEGORY_BASED,
                        'semantic_similarity': ClusteringStrategy.SEMANTIC_SIMILARITY,
                        'hybrid': ClusteringStrategy.HYBRID
                    }
                    strategy = strategy_map.get(args.clustering_strategy, ClusteringStrategy.CATEGORY_BASED)
                    
                    print(f"   Clustering {len(all_functions)} functions using {args.clustering_strategy} strategy...")
                    
                    # Create clusters
                    clusters = await clustering_system.get_current_function_clusters(all_functions, strategy)
                    
                    # Display cluster summary
                    print(f"\n   📊 Clustering Results:")
                    print(f"      Created {len(clusters)} function groups")
                    
                    for i, cluster in enumerate(clusters, 1):
                        if hasattr(args, 'verbose') and args.verbose:
                            print(f"\n   🏷️  Group {i}: {cluster.label}")
                            print(f"      Functions: {len(cluster.functions)} (confidence: {cluster.confidence:.2f})")
                            for func in cluster.functions[:3]:  # Show first 3 functions
                                print(f"      - {func['name']} ({func.get('file_path', 'unknown')})")
                            if len(cluster.functions) > 3:
                                print(f"      - ... and {len(cluster.functions) - 3} more")
                        else:
                            print(f"      Group {i}: {cluster.label} ({len(cluster.functions)} functions, confidence: {cluster.confidence:.2f})")
                    
                    # Identify clusters that need splitting
                    split_candidates = clustering_system.select_clusters_that_need_manual_split(clusters)
                    if split_candidates:
                        print(f"\n   ✂️  Split Candidates: {len(split_candidates)} large/complex groups could benefit from manual splitting")
                        for candidate in split_candidates[:3]:  # Show first 3 candidates
                            reason = "large size" if len(candidate.functions) > clustering_system.max_cluster_size else "low confidence"
                            print(f"      - {candidate.label}: {len(candidate.functions)} functions ({reason})")
                    
                    # Show clustering insights
                    insights = clustering_system.get_clustering_insights()
                    summary = insights['clustering_summary']
                    print(f"\n   📈 Insights:")
                    print(f"      Average group size: {summary['average_cluster_size']:.1f}")
                    if summary['split_history']['total_splits'] > 0:
                        print(f"      Split success rate: {summary['split_history']['success_rate']:.1%}")
                    
                    if hasattr(args, 'verbose') and args.verbose:
                        print(f"      💡 Use clustering to understand code organization patterns")
                        print(f"      💡 Large groups may indicate opportunities for refactoring")
                else:
                    print("   No functions found for clustering analysis")
            
            # Exit early if classification-only mode
            if args.classification_only or args.disable_duplicate_detection:
                return 0
            
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
                                print(format_semantic_duplicate(semantic_detector.structural_detector, sem_dup, i))
                            
                            if len(semantic_duplicates) > 5:
                                print(f"\n... and {len(semantic_duplicates) - 5} more semantic duplicates")
                        else:
                            print(f"\n✅ No semantic duplicates found above threshold {args.semantic_threshold}")
                        
                        # Show analysis summary - detailed if verbose, concise otherwise
                        summary = semantic_results.get('summary', {})
                        if summary:
                            if hasattr(args, 'verbose') and args.verbose:
                                print(f"\n📊 Semantic Analysis Summary:")
                                print(f"   Total records analyzed: {summary.get('total_code_records', 0)}")
                                print(f"   Semantic analyses attempted: {summary.get('semantic_analysis_attempted', 0)}")
                                print(f"   Successful analyses: {summary.get('semantic_analysis_successful', 0)}")
                                print(f"   Failed analyses: {summary.get('semantic_analysis_failed', 0)}")
                                print(f"   Recommendation: {summary.get('recommendation', 'N/A')}")
                            elif summary.get('recommendation'):
                                print(f"\n📊 Analysis Summary: {summary.get('recommendation', 'N/A')}")
                        
                        # Intent tree analysis - show based on verbose setting
                        intent_tree_results = semantic_results.get('intent_tree_analysis', {})
                        if intent_tree_results.get('available', False):
                            if hasattr(args, 'verbose') and args.verbose:
                                print(f"\n🎯 Intent Tree Analysis:")
                                print(f"   Added snippets: {intent_tree_results.get('added_snippets', 0)}")
                                print(f"   Generated features: {intent_tree_results.get('generated_features', 0)}")
                                print(f"   Exploration sessions: {len(intent_tree_results.get('exploration_sessions', []))}")
                                
                                # Show generated features
                                features = intent_tree_results.get('features', [])
                                if features:
                                    print(f"   Available patterns for analysis:")
                                    for i, feature in enumerate(features[:5], 1):
                                        print(f"     {i}. {feature['description']}: {feature['pattern']}")
                                    if len(features) > 5:
                                        print(f"     ... and {len(features) - 5} more patterns")
                            elif intent_tree_results.get('added_snippets', 0) > 0:
                                print(f"\n🎯 Learning: Added {intent_tree_results.get('added_snippets', 0)} new patterns for future analysis")
                        
                        
                        # Akinator-style detailed analysis
                        if args.use_akinator and semantic_detector and semantic_duplicates:
                            if hasattr(args, 'verbose') and args.verbose:
                                print(f"\n🎯 Akinator-Style Detailed Analysis:")
                                print(f"   Analyzing top {min(3, len(semantic_duplicates))} duplicate pairs...")
                            else:
                                print(f"\n🎯 Advanced Pattern Analysis: Enhanced {min(3, len(semantic_duplicates))} pairs with ML patterns")
                            
                            for i, sem_dup in enumerate(semantic_duplicates[:3], 1):
                                # Perform Akinator analysis silently
                                if sem_dup.code_record_1.code_content:
                                    try:
                                        akinator_result = await semantic_detector.explore_code_interactively(
                                            sem_dup.code_record_1.code_content
                                        )
                                        
                                        if akinator_result.get('available', False):
                                            session_id = akinator_result['session_id']
                                            questions_asked = 0
                                            analysis_results = []
                                            
                                            # Process pattern analysis silently
                                            while questions_asked < args.akinator_questions:
                                                question = akinator_result.get('question')
                                                if not question:
                                                    break
                                                
                                                questions_asked += 1
                                                
                                                # Auto-answer using regex matching
                                                import re
                                                try:
                                                    pattern = re.compile(question['pattern'], re.MULTILINE | re.DOTALL)
                                                    matches = bool(pattern.search(sem_dup.code_record_1.code_content))
                                                    
                                                    # Process the answer silently
                                                    answer_result = await semantic_detector.answer_exploration_question(
                                                        session_id, question['feature_id'], matches
                                                    )
                                                    
                                                    if answer_result and answer_result.get('available', False):
                                                        if answer_result['status'] == 'completed':
                                                            break
                                                        else:
                                                            akinator_result = answer_result
                                                    else:
                                                        break
                                                        
                                                except re.error:
                                                    break
                                            
                                            # Only show brief result
                                            print(f"   ✅ Enhanced analysis completed for {sem_dup.code_record_1.function_name} vs {sem_dup.code_record_2.function_name}")
                                                    
                                    except Exception as e:
                                        # Log error but continue processing
                                        if args.log_level == "DEBUG":
                                            print(f"   ⚠️  Enhanced analysis skipped: {e}")
                                        
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
                    return 0
            
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
        
        elif args.command == "akinator":
            # Interactive Akinator-style code exploration
            if not semantic_detector:
                print("❌ Akinator mode requires semantic analysis")
                print("   Please ensure intent_tree is available")
                return 1
                
            print("🎯 Starting Akinator-style code exploration...")
            print("   This will ask you questions to find similar code")
            print()
            
            try:
                # Start exploration session
                exploration_result = await semantic_detector.explore_code_interactively(args.code)
                
                if not exploration_result.get("available", False):
                    print(f"❌ Exploration not available: {exploration_result.get('reason', 'Unknown error')}")
                    return 1
                
                session_id = exploration_result["session_id"]
                question_count = 0
                
                print(f"🔍 Exploring code (session: {session_id[:8]}...)")
                print(f"📝 Query code preview:")
                print(f"   {args.code[:100]}...")
                print()
                
                # Interactive question loop
                while question_count < args.max_questions:
                    question = exploration_result.get("question")
                    if not question:
                        print("✅ No more questions needed")
                        break
                    
                    question_count += 1
                    print(f"❓ Question {question_count}/{args.max_questions}:")
                    print(f"   {question['question_text']}")
                    print(f"   Pattern: {question['pattern']}")
                    print(f"   Expected impact: {question['expected_impact']:.3f}")
                    print()
                    
                    # Get user answer or auto-answer
                    if args.auto_answer:
                        # Auto-answer using regex matching
                        import re
                        try:
                            pattern = re.compile(question['pattern'], re.MULTILINE | re.DOTALL)
                            matches = bool(pattern.search(args.code))
                            answer = "yes" if matches else "no"
                            print(f"🤖 Auto-answer: {answer}")
                        except re.error:
                            answer = "no"
                            print(f"🤖 Auto-answer: {answer} (invalid regex)")
                    else:
                        # Interactive mode
                        while True:
                            try:
                                response = input("   Does this pattern match your code? (yes/no/quit): ").strip().lower()
                                if response in ['yes', 'y']:
                                    answer = "yes"
                                    break
                                elif response in ['no', 'n']:
                                    answer = "no"
                                    break
                                elif response in ['quit', 'q']:
                                    print("🛑 Exploration cancelled")
                                    return 0
                                else:
                                    print("   Please answer 'yes', 'no', or 'quit'")
                            except KeyboardInterrupt:
                                print("\n🛑 Exploration cancelled")
                                return 0
                    
                    # Process answer
                    matches = answer == "yes"
                    result = await semantic_detector.answer_exploration_question(
                        session_id, question['feature_id'], matches
                    )
                    
                    if not result.get("available", False):
                        print(f"❌ Failed to process answer: {result.get('reason', 'Unknown error')}")
                        break
                    
                    print(f"✅ Answer recorded: {answer}")
                    
                    if result["status"] == "completed":
                        print(f"🎉 Exploration completed!")
                        final_result = result.get("result")
                        if final_result:
                            if final_result["type"] == "existing":
                                snippet = final_result["snippet"]
                                print(f"📋 Found matching code:")
                                print(f"   Function: {snippet.get('function_name', 'N/A')}")
                                print(f"   File: {snippet.get('file_path', 'N/A')}")
                                print(f"   Hash: {snippet.get('code_hash', 'N/A')[:16]}...")
                                if snippet.get('code_content'):
                                    print(f"   Code preview: {snippet['code_content'][:200]}...")
                            else:
                                print(f"💡 No existing code found - your code appears to be unique!")
                        break
                    else:
                        candidates = result.get("candidates", [])
                        print(f"🔍 {len(candidates)} candidates remaining")
                        exploration_result = result  # Update for next iteration
                        print()
                
                if question_count >= args.max_questions:
                    print(f"⏰ Reached maximum questions ({args.max_questions})")
                    print("   Consider increasing --max-questions for more thorough exploration")
                
                # Show learning statistics if requested
                if args.show_learning:
                    print(f"\n📊 Learning Statistics:")
                    try:
                        stats = await semantic_detector.get_learning_statistics()
                        if stats.get("available", False):
                            print(f"   Total features: {stats.get('total_features', 0)}")
                            print(f"   Total usage: {stats.get('total_usage', 0)}")
                            print(f"   Average information gain: {stats.get('avg_information_gain', 0):.3f}")
                            
                            most_used = stats.get('most_used_features', [])
                            if most_used:
                                print(f"   Most used features:")
                                for i, feature in enumerate(most_used[:3], 1):
                                    print(f"     {i}. {feature['description']}: {feature['match_count']} uses (gain: {feature['information_gain']:.3f})")
                            
                            most_effective = stats.get('most_effective_features', [])
                            if most_effective:
                                print(f"   Most effective features:")
                                for i, feature in enumerate(most_effective[:3], 1):
                                    print(f"     {i}. {feature['description']}: gain {feature['information_gain']:.3f} ({feature['match_count']} uses)")
                                    
                            # Show optimization potential
                            optimization = await semantic_detector.optimize_features_from_history()
                            if optimization.get("available", False):
                                print(f"   Optimization potential: {optimization.get('optimization_potential', False)}")
                                suggestions = optimization.get('new_feature_suggestions', [])
                                if suggestions:
                                    print(f"   New feature suggestions:")
                                    for i, suggestion in enumerate(suggestions[:2], 1):
                                        print(f"     {i}. {suggestion['description']} (based on {suggestion['based_on']})")
                        else:
                            print(f"   Learning statistics not available: {stats.get('reason', 'Unknown')}")
                    except Exception as e:
                        print(f"   Failed to get learning statistics: {e}")
                    
            except Exception as e:
                print(f"❌ Akinator exploration failed: {e}")
                if args.log_level == "DEBUG":
                    import traceback
                    traceback.print_exc()
                return 1
            
        else:
            parser.print_help()
            
    except OOPSTrackerError as e:
        print(f"❌ OOPStracker error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n⏹️  Operation interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
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