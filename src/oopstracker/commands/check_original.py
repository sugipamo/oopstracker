"""
Check command implementation for OOPStracker CLI.
"""
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base import BaseCommand, CommandContext
from ..models import CodeRecord
from ..ignore_patterns import IgnorePatterns
from ..progress_reporter import ProgressReporter
from .analyzers import (
    DuplicateAnalyzer,
    ClassificationAnalyzer,
    ClusteringAnalyzer,
    SemanticAnalyzer
)


class CheckCommand(BaseCommand):
    """Command to analyze code structure and function groups."""
    
    async def execute(self) -> int:
        """Execute the check command."""
        args = self.args
        detector = self.detector
        semantic_detector = self.semantic_detector
        
        # If duplicates-only mode, skip file scanning
        if args.duplicates_only:
            analyzer = DuplicateAnalyzer(self)
            result = await analyzer.analyze()
            analyzer.display_results(result)
            return 0
            
        # Main check command: scan changed files and detect duplicates
        path = Path(args.path)
        print(f"🔍 Checking {path} for updates and duplicates...")
        
        # Initialize ignore patterns
        ignore_patterns = IgnorePatterns(
            project_root=str(path if path.is_dir() else path.parent),
            use_gitignore=not args.no_gitignore,
            include_tests=args.include_tests
        )
        
        # Collect and scan files
        all_files = self._collect_files(path, args.pattern, ignore_patterns)
        print(f"📁 Found {len(all_files)} Python files")
        
        # Check for deleted files
        deleted_files = self._check_deleted_files(all_files)
        if deleted_files:
            print(f"🗑️  {len(deleted_files)} tracked files no longer exist (excluded from duplicate detection)")
        
        # Determine which files to scan
        files_to_scan = self._get_files_to_scan(all_files)
        
        # Scan changed files
        scan_results = await self._scan_files(files_to_scan)
        
        # Display scan summary
        self._display_scan_summary(scan_results)
        
        # Exit early if classification-only mode
        if args.classification_only or args.disable_duplicate_detection:
            return 0
            
        # Check project-wide duplicates
        duplicates = None
        if args.enable_duplicate_detection and not (args.classification_only or args.disable_duplicate_detection):
            duplicate_analyzer = DuplicateAnalyzer(self)
            duplicate_result = await duplicate_analyzer.analyze()
            duplicate_analyzer.display_results(duplicate_result)
            duplicates = duplicate_result.data.get('duplicates', [])
            
        # Run function classification
        classification_analyzer = ClassificationAnalyzer(self)
        classification_result = await classification_analyzer.analyze()
        classification_analyzer.display_results(classification_result)
        
        # Run clustering analysis if enabled
        if hasattr(args, 'enable_clustering') and args.enable_clustering:
            clustering_analyzer = ClusteringAnalyzer(self)
            clustering_result = await clustering_analyzer.analyze()
            clustering_analyzer.display_results(clustering_result)
            
        # Run semantic analysis if enabled
        if semantic_detector and hasattr(args, 'semantic_analysis') and args.semantic_analysis:
            semantic_analyzer = SemanticAnalyzer(self)
            semantic_result = await semantic_analyzer.analyze(duplicates=duplicates)
            semantic_analyzer.display_results(semantic_result)
            
        return 0
        
    def _collect_files(self, path: Path, pattern: str, ignore_patterns: IgnorePatterns) -> List[str]:
        """Collect files to check."""
        if path.is_file():
            return [str(path)] if not ignore_patterns.should_ignore(path) else []
        else:
            all_files = []
            for file_path in path.rglob(pattern):
                if file_path.is_file() and not ignore_patterns.should_ignore(file_path):
                    all_files.append(str(file_path))
            return all_files
            
    def _check_deleted_files(self, current_files: List[str]) -> List[str]:
        """Check for deleted files."""
        current_files_set = set(current_files)
        return self.detector.db_manager.check_and_mark_deleted_files(current_files_set)
        
    def _get_files_to_scan(self, all_files: List[str]) -> List[str]:
        """Determine which files to scan."""
        if self.args.force:
            files_to_scan = all_files
            print(f"🔄 Force mode: scanning all {len(files_to_scan)} files")
        else:
            changed_files = self.detector.db_manager.get_changed_files(all_files)
            files_to_scan = changed_files
            print(f"📝 {len(changed_files)} files have changed since last scan")
        return files_to_scan
        
    async def _scan_files(self, files_to_scan: List[str]) -> Dict[str, Any]:
        """Scan files and collect results."""
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
            
            records = self.detector.register_file(file_path, force=self.args.force)
            if records:
                new_records.extend(records)
                updated_files += 1
                
                # Check for duplicates in newly registered code
                for record in records:
                    if record.metadata and record.metadata.get('type') == 'module':
                        continue
                    
                    result = self.detector.find_similar(
                        record.code_content, 
                        record.function_name, 
                        file_path
                    )
                    
                    if result.is_duplicate and result.matched_records:
                        # Collect duplicate info for summary
                        dup_info = self._create_duplicate_info(record, result, file_path)
                        if dup_info['matches']:
                            duplicates_found.append(dup_info)
        
        return {
            'new_records': new_records,
            'updated_files': updated_files,
            'duplicates': duplicates_found
        }
        
    def _create_duplicate_info(self, record: CodeRecord, result: Any, file_path: str) -> Dict[str, Any]:
        """Create duplicate info for summary."""
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
        
        return dup_info
        
    def _display_scan_summary(self, scan_results: Dict[str, Any]):
        """Display scan summary."""
        print(f"\n📊 Summary:")
        print(f"   Files scanned: {scan_results['updated_files']}")
        print(f"   New/updated code units: {len(scan_results['new_records'])}")
        
        # Show duplicates if found
        duplicates_found = scan_results.get('duplicates', [])
        if duplicates_found:
            print(f"\n⚠️  Found {len(duplicates_found)} duplicates:")
            for dup in duplicates_found[:10]:  # Show first 10
                print(f"\n   {dup['type']}: '{dup['name']}' in {dup['file']}")
                for match in dup['matches'][:2]:  # Show first 2 matches
                    print(f"      Similar to: {match['name']} in {match['file']} (similarity: {match['similarity']:.3f})")
            
            if len(duplicates_found) > 10:
                print(f"\n   ... and {len(duplicates_found) - 10} more duplicates")
                
    @classmethod
    def add_arguments(cls, parser):
        """Add command-specific arguments to the parser."""
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
            "--no-gitignore",
            action="store_true",
            help="Don't use .gitignore patterns"
        )
        advanced_group.add_argument(
            "--include-tests",
            action="store_true",
            help="Include test files in analysis"
        )
        advanced_group.add_argument(
            "--force", "-f",
            action="store_true",
            help="Force re-scan all files"
        )
        
        # Duplicate detection options
        dup_group = parser.add_argument_group('duplicate detection options')
        dup_group.add_argument(
            "--duplicates-only",
            action="store_true",
            help="Only show duplicates without rescanning files"
        )
        dup_group.add_argument(
            "--threshold", "-t",
            type=float,
            default=0.7,
            help="Similarity threshold for duplicate detection (0.0-1.0, default: 0.7)"
        )
        dup_group.add_argument(
            "--similarity-threshold",
            type=float,
            default=0.85,
            help="Similarity threshold (default: 0.85)"
        )
        dup_group.add_argument(
            "--exhaustive",
            action="store_true",
            help="Use exhaustive (slower but more accurate) duplicate detection"
        )
        dup_group.add_argument(
            "--include-trivial",
            action="store_true",
            help="Include trivial duplicates (simple classes, etc.)"
        )
        dup_group.add_argument(
            "--top-percent",
            type=float,
            help="Show top X percent of similar pairs (e.g., 5 for top 5%%)"
        )
        dup_group.add_argument(
            "--limit",
            type=int,
            default=15,
            help="Maximum number of duplicate pairs to display (default: 15)"
        )
        
        # Clustering options
        cluster_group = parser.add_argument_group('clustering options')
        cluster_group.add_argument(
            "--enable-clustering",
            action="store_true",
            help="Enable function clustering analysis"
        )
        cluster_group.add_argument(
            "--clustering-strategy",
            choices=['category_based', 'semantic_similarity', 'hybrid'],
            default='category_based',
            help="Clustering strategy to use (default: category_based)"
        )
        
        # Semantic analysis options
        semantic_group = parser.add_argument_group('semantic analysis options')
        semantic_group.add_argument(
            "--semantic-analysis",
            action="store_true",
            help="Enable semantic duplicate analysis (requires AI)"
        )
        semantic_group.add_argument(
            "--semantic-threshold",
            type=float,
            default=0.8,
            help="Threshold for semantic similarity (default: 0.8)"
        )
        semantic_group.add_argument(
            "--max-semantic-concurrent",
            type=int,
            default=3,
            help="Maximum concurrent semantic analyses (default: 3)"
        )
        semantic_group.add_argument(
            "--use-akinator",
            action="store_true",
            help="Use Akinator-style pattern classification"
        )
        
        # Debug options
        debug_group = parser.add_argument_group('debug options')
        debug_group.add_argument(
            "--log-level",
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            default='WARNING',
            help="Set logging level (default: WARNING)"
        )