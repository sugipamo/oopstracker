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
from ..function_taxonomy_expert import FunctionTaxonomyExpert
from ..function_group_clustering import FunctionGroupClusteringSystem, ClusteringStrategy


class CheckCommand(BaseCommand):
    """Command to analyze code structure and function groups."""
    
    async def execute(self) -> int:
        """Execute the check command."""
        args = self.args
        detector = self.detector
        semantic_detector = self.semantic_detector
        
        # If duplicates-only mode, skip file scanning
        if args.duplicates_only:
            return await self._execute_duplicates_only()
            
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
        if args.enable_duplicate_detection and not (args.classification_only or args.disable_duplicate_detection):
            await self._check_duplicates()
            
        # Run function classification
        await self._run_function_classification()
        
        # Run clustering analysis if enabled
        if hasattr(args, 'enable_clustering') and args.enable_clustering:
            await self._run_clustering_analysis()
            
        # Run semantic analysis if enabled
        if semantic_detector and hasattr(args, 'semantic_analysis') and args.semantic_analysis:
            await self._run_semantic_analysis(scan_results.get('duplicates', []))
            
        return 0
        
    async def _execute_duplicates_only(self) -> int:
        """Execute duplicates-only mode."""
        print("🔍 Finding potential duplicates...")
        use_fast_mode = not self.args.exhaustive
        
        # Use dynamic threshold by default (top 3%) if not specified
        if self.args.top_percent is None:
            default_top_percent = 3.0
            pairs = self.detector.find_potential_duplicates(
                threshold=0.7, 
                use_fast_mode=use_fast_mode, 
                include_trivial=self.args.include_trivial, 
                silent=False, 
                top_percent=default_top_percent
            )
            threshold_display = f"dynamic (top {default_top_percent}%)"
        else:
            threshold = self.args.threshold if self.args.threshold else self.args.similarity_threshold
            pairs = self.detector.find_potential_duplicates(
                threshold=threshold, 
                use_fast_mode=use_fast_mode, 
                include_trivial=self.args.include_trivial, 
                silent=False, 
                top_percent=self.args.top_percent
            )
            threshold_display = f"dynamic (top {self.args.top_percent}%)"
        
        if not pairs:
            print("✅ No duplicates found")
        else:
            print(f"⚠️  Found {len(pairs)} potential duplicate pairs ({threshold_display}):")
            for i, (unit1, unit2, similarity) in enumerate(pairs[:self.args.limit], 1):
                print(self._format_duplicate_pair(unit1, unit2, similarity, i))
        
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
                
    async def _check_duplicates(self):
        """Check project-wide duplicates."""
        print(f"\n🔍 Checking all duplicates in project...")
        use_fast_mode = not self.args.exhaustive
        
        # Use dynamic threshold by default (top 3%) if not specified
        if self.args.top_percent is None:
            default_top_percent = 3.0
            duplicates = self.detector.find_potential_duplicates(
                threshold=0.7, 
                use_fast_mode=use_fast_mode, 
                include_trivial=self.args.include_trivial, 
                silent=False, 
                top_percent=default_top_percent
            )
            threshold_display = f"dynamic (top {default_top_percent}%)"
        else:
            threshold = 0.7
            duplicates = self.detector.find_potential_duplicates(
                threshold=threshold, 
                use_fast_mode=use_fast_mode, 
                include_trivial=self.args.include_trivial, 
                silent=False, 
                top_percent=self.args.top_percent
            )
            threshold_display = f"dynamic (top {self.args.top_percent}%)"
        
        if duplicates:
            print(f"\n⚠️  Found {len(duplicates)} potential duplicate pairs ({threshold_display}):")
            display_limit = 15
            for i, (record1, record2, similarity) in enumerate(duplicates[:display_limit], 1):
                print(self._format_duplicate_pair(record1, record2, similarity, i))
            
            if len(duplicates) > display_limit:
                print(f"\n... and {len(duplicates) - display_limit} more pairs")
            
            # Show helpful tips
            if not self.args.include_trivial:
                print(f"\n💡 Use --include-trivial to see all duplicates (including simple classes)")
            print(f"💡 Use --top-percent X to adjust sensitivity ({threshold_display})")
            print(f"💡 Use --exhaustive for higher accuracy (slower)")
        else:
            print(f"\n✅ No meaningful duplicates found ({threshold_display})!")
            print(f"💡 Try --include-trivial or lower --top-percent for more results")
            
    async def _run_function_classification(self):
        """Run function classification analysis."""
        print(f"\n🎯 Function Classification Analysis")
        
        taxonomy_expert = FunctionTaxonomyExpert(enable_ai=True)
        
        # Get all functions from detector
        function_units = [unit for unit in self.detector.code_units.values() 
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
                
                if hasattr(self.args, 'verbose') and self.args.verbose:
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
            
    async def _run_clustering_analysis(self):
        """Run function group clustering analysis."""
        print(f"\n🔬 Function Group Clustering Analysis")
        
        clustering_system = FunctionGroupClusteringSystem(enable_ai=True)
        
        # Load functions from detector
        all_functions = await clustering_system.load_all_functions_from_repository(
            list(self.detector.code_units.values())
        )
        
        if all_functions:
            # Convert strategy string to enum
            strategy_map = {
                'category_based': ClusteringStrategy.CATEGORY_BASED,
                'semantic_similarity': ClusteringStrategy.SEMANTIC_SIMILARITY,
                'hybrid': ClusteringStrategy.HYBRID
            }
            strategy = strategy_map.get(
                self.args.clustering_strategy, 
                ClusteringStrategy.CATEGORY_BASED
            )
            
            print(f"   Clustering {len(all_functions)} functions using {self.args.clustering_strategy} strategy...")
            
            # Create clusters
            clusters = await clustering_system.get_current_function_clusters(all_functions, strategy)
            
            # Display cluster summary
            print(f"\n   📊 Clustering Results:")
            print(f"      Created {len(clusters)} function groups")
            
            for i, cluster in enumerate(clusters, 1):
                if hasattr(self.args, 'verbose') and self.args.verbose:
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
            
            if hasattr(self.args, 'verbose') and self.args.verbose:
                print(f"      💡 Use clustering to understand code organization patterns")
                print(f"      💡 Large groups may indicate opportunities for refactoring")
        else:
            print("   No functions found for clustering analysis")
            
    async def _run_semantic_analysis(self, duplicates: List[Any]):
        """Run semantic analysis on duplicates."""
        print(f"\n🧠 Performing semantic analysis...")
        try:
            # Convert structural duplicates to CodeRecords for semantic analysis
            code_records = []
            for record1, record2, similarity in duplicates[:10]:  # Limit to top 10
                code_records.extend([record1, record2])
            
            # Remove duplicates from code_records
            unique_records = []
            seen_hashes = set()
            for record in code_records:
                if record.code_hash not in seen_hashes:
                    unique_records.append(record)
                    seen_hashes.add(record.code_hash)
            
            if unique_records:
                semantic_results = await self.semantic_detector.detect_duplicates(
                    code_records=unique_records,
                    enable_semantic=True,
                    semantic_threshold=self.args.semantic_threshold,
                    max_concurrent=self.args.max_semantic_concurrent
                )
                
                semantic_duplicates = semantic_results.get('semantic_duplicates', [])
                if semantic_duplicates:
                    print(f"\n🔍 Semantic analysis found {len(semantic_duplicates)} meaningful duplicates:")
                    for i, sem_dup in enumerate(semantic_duplicates[:5], 1):
                        print(self._format_semantic_duplicate(sem_dup, i))
                    
                    if len(semantic_duplicates) > 5:
                        print(f"\n... and {len(semantic_duplicates) - 5} more semantic duplicates")
                else:
                    print(f"\n✅ No semantic duplicates found above threshold {self.args.semantic_threshold}")
                
                # Show analysis summary
                self._display_semantic_summary(semantic_results)
                
                # Intent tree analysis
                self._display_intent_tree_analysis(semantic_results)
                
                # Akinator-style detailed analysis
                if self.args.use_akinator and self.semantic_detector and semantic_duplicates:
                    await self._run_akinator_analysis(semantic_duplicates)
                    
            else:
                print(f"\n📝 No structural duplicates available for semantic analysis")
                
        except Exception as e:
            print(f"\n❌ Semantic analysis failed: {e}")
            if self.args.log_level == "DEBUG":
                import traceback
                traceback.print_exc()
                
    def _display_semantic_summary(self, semantic_results: Dict[str, Any]):
        """Display semantic analysis summary."""
        summary = semantic_results.get('summary', {})
        if summary:
            if hasattr(self.args, 'verbose') and self.args.verbose:
                print(f"\n📊 Semantic Analysis Summary:")
                print(f"   Total records analyzed: {summary.get('total_code_records', 0)}")
                print(f"   Semantic analyses attempted: {summary.get('semantic_analysis_attempted', 0)}")
                print(f"   Successful analyses: {summary.get('semantic_analysis_successful', 0)}")
                print(f"   Failed analyses: {summary.get('semantic_analysis_failed', 0)}")
                print(f"   Recommendation: {summary.get('recommendation', 'N/A')}")
            elif summary.get('recommendation'):
                print(f"\n📊 Analysis Summary: {summary.get('recommendation', 'N/A')}")
                
    def _display_intent_tree_analysis(self, semantic_results: Dict[str, Any]):
        """Display intent tree analysis results."""
        intent_tree_results = semantic_results.get('intent_tree_analysis', {})
        if intent_tree_results.get('available', False):
            if hasattr(self.args, 'verbose') and self.args.verbose:
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
                
    async def _run_akinator_analysis(self, semantic_duplicates: List[Any]):
        """Run Akinator-style analysis on semantic duplicates."""
        if hasattr(self.args, 'verbose') and self.args.verbose:
            print(f"\n🎯 Akinator-Style Detailed Analysis:")
            print(f"   Analyzing top {min(3, len(semantic_duplicates))} duplicate pairs...")
        else:
            print(f"\n🎯 Advanced Pattern Analysis: Enhanced {min(3, len(semantic_duplicates))} pairs with ML patterns")
        
        for i, sem_dup in enumerate(semantic_duplicates[:3], 1):
            # Perform Akinator analysis silently
            if sem_dup.code_record_1.code_content:
                try:
                    akinator_result = await self.semantic_detector.explore_code_interactively(
                        sem_dup.code_record_1.code_content
                    )
                    
                    if akinator_result.get('available', False):
                        session_id = akinator_result['session_id']
                        questions_asked = 0
                        
                        # Process pattern analysis silently
                        while questions_asked < self.args.akinator_questions:
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
                                answer_result = await self.semantic_detector.answer_exploration_question(
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
                    if self.args.log_level == "DEBUG":
                        print(f"   ⚠️  Enhanced analysis skipped: {e}")
                        
    def _format_duplicate_pair(self, record1: CodeRecord, record2: CodeRecord, similarity: float, index: int) -> str:
        """Format duplicate pair for display."""
        # Get detailed unit information
        unit1 = self.detector.code_units.get(record1.code_hash)
        unit2 = self.detector.code_units.get(record2.code_hash)
        
        line1 = f":{unit1.start_line}" if unit1 and unit1.start_line else ""
        line2 = f":{unit2.start_line}" if unit2 and unit2.start_line else ""
        
        type1 = record1.metadata.get('type', 'unknown') if record1.metadata else 'unknown'
        type2 = record2.metadata.get('type', 'unknown') if record2.metadata else 'unknown'
        
        output = [
            f"\n{index}. {type1}: {record1.function_name or 'N/A'} ({record1.file_path or 'N/A'}{line1})",
            f"   ≈ {type2}: {record2.function_name or 'N/A'} ({record2.file_path or 'N/A'}{line2})",
            f"   Similarity: {similarity:.3f}"
        ]
        
        return "\n".join(output)
        
    def _format_semantic_duplicate(self, sem_dup: Any, index: int) -> str:
        """Format semantic duplicate for display."""
        output = [
            f"\n{index}. {sem_dup.code_record_1.function_name} ≈ {sem_dup.code_record_2.function_name}",
            f"   Semantic Similarity: {sem_dup.semantic_similarity:.3f}",
            f"   Structural Similarity: {sem_dup.structural_similarity:.3f}",
            f"   File 1: {sem_dup.code_record_1.file_path}",
            f"   File 2: {sem_dup.code_record_2.file_path}",
            f"   Analysis: {sem_dup.llm_analysis[:100]}..." if len(sem_dup.llm_analysis) > 100 else f"   Analysis: {sem_dup.llm_analysis}"
        ]
        
        return "\n".join(output)
        
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
        
        # Legacy duplicate detection
        legacy_group = parser.add_argument_group('legacy duplicate detection')
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