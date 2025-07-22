"""
Refactored check command for OOPStracker.
Analyzes code structure and function groups with improved modularity.
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from ..models import CodeRecord
from ..ast_simhash_detector import ASTSimHashDetector
from ..progress_reporter import ProgressReporter
from ..services.file_scan_service import FileScanService
from ..services.duplicate_detection_service import DuplicateDetectionService
from ..services.classification_service import ClassificationService
from ..services.clustering_service import ClusteringService
from .base import BaseCommand


class CheckCommand(BaseCommand):
    """Analyze code structure and function groups with smart defaults."""
    
    @classmethod
    def add_arguments(cls, parser: argparse.ArgumentParser):
        """Add command-specific arguments."""
        parser.add_argument(
            "path",
            nargs="?",
            default=".",
            help="Directory or file to analyze (default: current directory)"
        )
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Show detailed analysis for each function group"
        )
        parser.add_argument(
            "--quiet", "-q",
            action="store_true",
            help="Show only summary statistics"
        )
        parser.add_argument(
            "--no-clustering",
            action="store_true",
            help="Disable automatic function grouping"
        )
        parser.add_argument(
            "--enable-duplicate-detection",
            action="store_true",
            help="Enable duplicate detection (disabled by default)"
        )
        parser.add_argument(
            "--disable-duplicate-detection",
            action="store_true",
            help="Disable duplicate detection"
        )
        parser.add_argument(
            "--classification-only",
            action="store_true",
            help="Only run classification, skip duplicate detection"
        )
        
        # Advanced options
        advanced_group = parser.add_argument_group('advanced options')
        advanced_group.add_argument(
            "--pattern", "-p",
            default="*.py",
            help="File pattern to match (default: *.py)"
        )
        advanced_group.add_argument(
            "--force", "-f",
            action="store_true",
            help="Force re-scan all files"
        )
        advanced_group.add_argument(
            "--top-percent",
            type=float,
            help="Show top X%% of duplicates (dynamic threshold)"
        )
        advanced_group.add_argument(
            "--exhaustive",
            action="store_true",
            help="Use exhaustive duplicate search (slower but more accurate)"
        )
        advanced_group.add_argument(
            "--include-trivial",
            action="store_true",
            help="Include trivial duplicates in results"
        )
        advanced_group.add_argument(
            "--enable-clustering",
            action="store_true",
            help="Enable function group clustering analysis"
        )
        advanced_group.add_argument(
            "--clustering-strategy",
            choices=['category_based', 'semantic_similarity', 'hybrid'],
            default='category_based',
            help="Clustering strategy to use"
        )
        
    async def execute(self, context, args) -> int:
        """Execute the check command."""
        detector = context.detector
        logger = logging.getLogger(__name__)
        
        # Initialize services
        file_scan_service = FileScanService(detector, logger)
        duplicate_service = DuplicateDetectionService(detector, logger)
        classification_service = ClassificationService(detector, logger)
        clustering_service = ClusteringService(detector, logger)
        
        # Check if database exists
        first_scan = not detector.db_manager.has_data()
        
        if first_scan:
            print("🔍 First time scanning this project...")
        
        # Step 1: File scanning
        print(f"📂 Scanning {args.path}")
        
        try:
            all_files = file_scan_service.find_files(args.path, args.pattern)
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1
            
        if not all_files:
            print(f"❌ No {args.pattern} files found in {args.path}")
            return 1
            
        # Determine which files to scan
        if args.force or first_scan:
            files_to_scan = all_files
            if first_scan:
                print(f"🔄 Analyzing {len(all_files)} files...")
            else:
                print(f"🔄 Force re-scanning {len(all_files)} files...")
        else:
            files_to_scan = file_scan_service.get_changed_files(all_files)
            print(f"📝 {len(files_to_scan)} files have changed since last scan")
            
        # Create progress reporter
        progress_reporter = ProgressReporter(
            interval_seconds=5.0,
            min_items_for_display=50,
            silent=args.quiet
        )
        
        # Scan files
        new_records, updated_files = await file_scan_service.scan_files(
            [Path(f) for f in files_to_scan],
            force=args.force,
            progress_reporter=progress_reporter
        )
        
        # Find duplicates in new records
        duplicates_found = []
        for file_path in files_to_scan:
            file_records = [r for r in new_records if r.file_path == str(file_path)]
            file_duplicates = file_scan_service.find_duplicates_in_records(
                file_records, 
                str(file_path)
            )
            duplicates_found.extend(file_duplicates)
            
        # Print summary
        if not args.quiet:
            print(f"\n📊 Summary:")
            print(f"   Files scanned: {updated_files}")
            print(f"   New/updated code units: {len(new_records)}")
            
            # Show duplicates found during scan
            if duplicates_found:
                print(duplicate_service.format_duplicate_summary(duplicates_found))
                
        # Step 2: Duplicate detection (if enabled)
        duplicates, threshold_display = await duplicate_service.find_duplicates(
            enable_detection=args.enable_duplicate_detection,
            classification_only=args.classification_only,
            disable_detection=args.disable_duplicate_detection,
            top_percent=args.top_percent,
            exhaustive=args.exhaustive,
            include_trivial=args.include_trivial
        )
        
        if not args.quiet:
            if duplicates:
                print(f"\n⚠️  Found {len(duplicates)} potential duplicate pairs ({threshold_display}):")
                print(duplicate_service.format_duplicate_pairs(duplicates, display_limit=15))
                print("\n" + duplicate_service.get_duplicate_tips(
                    duplicates, 
                    args.include_trivial, 
                    threshold_display
                ))
            else:
                print(f"\n✅ No meaningful duplicates found ({threshold_display})!")
                print(duplicate_service.get_duplicate_tips(
                    duplicates, 
                    args.include_trivial, 
                    threshold_display
                ))
                
        # Step 3: Function classification
        print(f"\n🎯 Function Classification Analysis")
        
        classification_results = await classification_service.classify_functions(
            verbose=args.verbose,
            limit=15
        )
        
        if not args.quiet:
            print(classification_service.format_classification_results(classification_results))
            
        # Step 4: Function clustering (if enabled)
        clustering_results = await clustering_service.cluster_functions(
            enable_clustering=args.enable_clustering,
            clustering_strategy=args.clustering_strategy,
            verbose=args.verbose,
            limit=10
        )
        
        if clustering_results['enabled'] and not args.quiet:
            print(clustering_service.format_clustering_results(clustering_results))
            
        return 0
