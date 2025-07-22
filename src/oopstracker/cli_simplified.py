"""
Simplified Command-line interface for OOPStracker.
Focused on function analysis and clustering as primary features.
"""

import argparse
import sys
import logging
import asyncio
from pathlib import Path
from typing import List

from .models import CodeRecord
from .exceptions import OOPSTrackerError
from .ignore_patterns import IgnorePatterns
from .ast_simhash_detector import ASTSimHashDetector
from .function_taxonomy_expert import FunctionTaxonomyExpert
from .function_group_clustering import FunctionGroupClusteringSystem, ClusteringStrategy
from .smart_group_splitter import SmartGroupSplitter
from .refactoring_advisor import RefactoringAdvisor


def setup_logging(level: str = "WARNING"):
    """Set up logging configuration."""
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.handlers = []
    root_logger.addHandler(handler)


async def run_check_command(detector, args):
    """Run the simplified check command focused on function analysis."""
    path = Path(args.path)
    
    # Set default attributes if not present
    if not hasattr(args, 'duplicates_only'):
        args.duplicates_only = False
    
    # Quick scan for changes
    print(f"🔍 Analyzing {path}...")
    
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
    
    # Check for changes (fast mode by default)
    current_files_set = set(all_files)
    deleted_files = detector.db_manager.check_and_mark_deleted_files(current_files_set)
    if deleted_files and not args.quiet:
        print(f"🗑️  {len(deleted_files)} tracked files removed")
    
    # Only scan changed files unless forced
    if args.force:
        files_to_scan = all_files
        if not args.quiet:
            print(f"🔄 Force mode: scanning all {len(files_to_scan)} files")
    else:
        changed_files = detector.db_manager.get_changed_files(all_files)
        files_to_scan = changed_files
        if changed_files and not args.quiet:
            print(f"📝 {len(changed_files)} files have changed")
    
    # Quick scan for changes
    updated_count = 0
    for file_path in files_to_scan:
        records = detector.register_file(file_path, force=args.force)
        if records:
            updated_count += 1
    
    if updated_count > 0 and not args.quiet:
        print(f"✅ Updated {updated_count} files")
    
    # Main functionality: Classification and Clustering
    print(f"\n🎯 Function Analysis")
    
    # Get all functions
    function_units = [unit for unit in detector.code_units.values() if unit.type == 'function']
    
    if not function_units:
        print("   No functions found to analyze")
        return 0
    
    print(f"   Found {len(function_units)} functions")
    
    # Check if clustering should be skipped (for performance)
    if hasattr(args, 'no_clustering') and args.no_clustering:
        print("   Clustering skipped (--no-clustering flag)")
        return 0
    
    # Initialize analysis systems
    clustering_system = FunctionGroupClusteringSystem(enable_ai=True)
    
    # Perform clustering analysis (main feature)
    all_functions = await clustering_system.load_all_functions_from_repository(list(detector.code_units.values()))
    
    # Use hierarchical clustering for better performance
    if len(all_functions) > 100:
        print(f"   Using hierarchical clustering for {len(all_functions)} functions (O(log N) optimization)")
        clusters = await clustering_system.hierarchical_cluster_and_classify(
            all_functions, 
            max_group_size=50,
            max_depth=8
        )
    else:
        clusters = await clustering_system.get_current_function_clusters(all_functions, ClusteringStrategy.CATEGORY_BASED)
    
    # Smart splitting: automatically subdivide large groups
    splitter = SmartGroupSplitter(enable_ai=True)
    original_cluster_count = len(clusters)
    groups_split = 0
    
    # First apply traditional pattern-based splitting for groups > 20
    intermediate_clusters = []
    for cluster in clusters:
        if splitter.should_split(cluster):
            # Split using predefined patterns
            subgroups = splitter.split_group_intelligently(cluster)
            intermediate_clusters.extend(subgroups)
            groups_split += 1
            
            if not args.quiet:
                print(f"   ✂️  Subdivided '{cluster.label}' ({len(cluster.functions)} functions) into {len(subgroups)} subgroups")
        else:
            intermediate_clusters.append(cluster)
    
    # Skip time-consuming process for better user experience
    final_clusters = intermediate_clusters
    
    # Process completed without advanced splitting
    llm_splits = 0
    
    # Replace clusters with final version
    clusters = final_clusters
    
    # Display split notification if any groups were split
    if groups_split > 0 and not args.quiet:
        print(f"   📊 Automatically subdivided {groups_split} large groups into {len(clusters)} total groups")
    
    # Display results based on verbosity
    if args.quiet:
        # Minimal output
        print(f"\n📊 Summary: {len(clusters)} function groups, {len(all_functions)} total functions")
        for cluster in clusters:
            print(f"   • {cluster.label}: {len(cluster.functions)} functions")
    else:
        # Standard output
        print(f"\n📊 Function Groups ({len(clusters)} groups)")
        for i, cluster in enumerate(clusters, 1):
            print(f"\n{i}. {cluster.label}")
            print(f"   Functions: {len(cluster.functions)} (confidence: {cluster.confidence:.2f})")
            
            if args.verbose:
                # Show sample functions
                for func in cluster.functions[:3]:
                    print(f"   - {func['name']} ({func.get('file_path', 'unknown')})")
                if len(cluster.functions) > 3:
                    print(f"   - ... and {len(cluster.functions) - 3} more")
        
        # Insights
        print(f"\n💡 Analysis Insights:")
        
        # Show if any groups were automatically split
        if groups_split > 0:
            print(f"   - Automatically subdivided {groups_split} large groups for better organization")
        
        # Show largest group (should now be much smaller after splitting)
        if clusters:
            largest = max(clusters, key=lambda c: len(c.functions))
            print(f"   - Largest group: {largest.label} ({len(largest.functions)} functions)")
        
        # Calculate distribution
        if clusters:
            avg_size = sum(len(c.functions) for c in clusters) / len(clusters)
            print(f"   - Average group size: {avg_size:.1f} functions")
        
        # Show well-balanced distribution
        small_groups = sum(1 for c in clusters if len(c.functions) <= 10)
        medium_groups = sum(1 for c in clusters if 10 < len(c.functions) <= 20)
        large_groups = sum(1 for c in clusters if len(c.functions) > 20)
        
        if small_groups > 0 or medium_groups > 0:
            print(f"   - Size distribution: {small_groups} small (≤10), {medium_groups} medium (11-20), {large_groups} large (>20)")
    
    # Generate refactoring proposals
    advisor = RefactoringAdvisor()
    proposals = advisor.analyze_groups_and_propose(clusters)
    
    if proposals and not args.quiet:
        proposals_text = advisor.format_proposals_for_display(proposals)
        print(proposals_text)
    
    # Legacy duplicate detection (only if explicitly requested)
    if hasattr(args, 'duplicates') and args.duplicates:
        print(f"\n🔍 Legacy Duplicate Detection")
        print("   (This feature is deprecated - consider using function groups instead)")
        
        threshold = args.duplicates_threshold
        pairs = detector.find_potential_duplicates(
            threshold=threshold, 
            use_fast_mode=True, 
            include_trivial=False, 
            silent=True
        )
        
        if pairs:
            print(f"   Found {len(pairs)} potential duplicates (threshold: {threshold})")
            for i, (unit1, unit2, similarity) in enumerate(pairs[:5], 1):
                print(f"   {i}. {unit1.function_name} ↔ {unit2.function_name} ({similarity:.3f})")
        else:
            print("   No duplicates found")
    
    return 0


async def async_main():
    """Async main function."""
    parser = argparse.ArgumentParser(
        description="OOPStracker - Code Analysis and Function Clustering"
    )
    parser.add_argument(
        "--db", "-d", 
        default="oopstracker.db",
        help="Database file path (default: oopstracker.db)"
    )
    parser.add_argument(
        "--log-level", "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="WARNING",
        help="Log level (default: WARNING)"
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
    advanced_group.add_argument(
        "--no-clustering",
        action="store_true",
        help="Skip clustering analysis (faster)"
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
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    # Initialize detector
    try:
        detector = ASTSimHashDetector(
            hamming_threshold=10,
            db_path=args.db,
            include_tests=getattr(args, 'include_tests', False)
        )
    except Exception as e:
        print(f"❌ Failed to initialize OOPStracker: {e}")
        sys.exit(1)
    
    # Handle commands
    try:
        if args.command == "check":
            return await run_check_command(detector, args)
        elif args.command is None:
            parser.print_help()
            return 0
        else:
            print(f"❌ Unknown command: {args.command}")
            parser.print_help()
            return 1
            
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


if __name__ == "__main__":
    main()