"""
Refactored check command using new architecture.
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from ..component_registry import ComponentRegistry
from ..unified_detector import UnifiedDetectionService
from ..unified_repository import UnifiedRepository
from ..refactored_analysis_service import RefactoredAnalysisService
from .base import BaseCommand


class CheckCommand(BaseCommand):
    """Analyze code structure and function groups with smart defaults."""
    
    @classmethod
    def help(cls) -> str:
        """Return help text for the check command."""
        return "Analyze code structure and detect duplicates"
    
    @classmethod
    def add_arguments(cls, parser: argparse.ArgumentParser):
        """Add command-specific arguments."""
        parser.add_argument(
            "code",
            nargs="?",
            default=".",
            help="Directory or file to analyze (default: current directory)"
        )
        
    async def execute(self) -> int:
        """Execute the check command using new architecture."""
        args = self.args
        
        # Initialize components
        component_registry = ComponentRegistry()
        
        # Create database manager
        db_manager = component_registry.create_component("database_manager", db_path="oopstracker.db")
        if not db_manager:
            print("❌ Failed to initialize database manager")
            return 1
        
        # Initialize database schema
        from ..database.schema_manager import SchemaManager
        schema_manager = SchemaManager(db_manager)
        schema_manager._create_tables()
        
        # Initialize services
        repository = UnifiedRepository(db_manager)
        detector = UnifiedDetectionService()
        analysis_service = RefactoredAnalysisService(repository, detector)
        
        # Find Python files
        files = self._find_python_files(args.code)
        if not files:
            print(f"❌ No Python files found in {args.code}")
            return 1
        
        print(f"🔍 Analyzing {len(files)} Python files...")
        
        # Process files in smaller batches to manage memory and rate limits
        batch_size = 10  # Reduced batch size to minimize LLM calls
        total_results = []
        
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(files)-1)//batch_size + 1} ({len(batch)} files)")
            
            # Add delay between batches to respect rate limits
            if i > 0:
                import time
                print("  Waiting to respect rate limits...")
                time.sleep(2)  # 2 second delay between batches
            
            # Perform analysis on batch
            result = analysis_service.analyze_files(batch)
            if not result.success:
                print(f"❌ Analysis failed on batch {i//batch_size + 1}: {result.error_message}")
                # Don't fail immediately - continue with remaining batches
                print("  Continuing with remaining batches...")
                continue
                
            total_results.append(result)
        
        # Combine results from all batches
        if total_results:
            result = total_results[0]  # Use first result as base
            for r in total_results[1:]:
                result.total_files += r.total_files
                result.processed_records += r.processed_records
                result.duplicates_found += r.duplicates_found
                if r.classifications:
                    for category, count in r.classifications.items():
                        result.classifications[category] = result.classifications.get(category, 0) + count
        
        if not result.success:
            print(f"❌ Analysis failed: {result.error_message}")
            return 1
        
        # Display results
        print(f"\n📊 Analysis Summary:")
        print(f"   Files processed: {result.total_files}")
        print(f"   Code records: {result.processed_records}")
        
        if result.duplicates_found > 0:
            print(f"   ⚠️  Duplicates found: {result.duplicates_found}")
        else:
            print(f"   ✅ No duplicates found")
        
        if result.classifications:
            print(f"\n📋 Classifications:")
            for category, count in result.classifications.items():
                print(f"   {category}: {count}")
        
        return 0
    
    def _find_python_files(self, path: str, max_files: int = 1000) -> list:
        """Find Python files in path with memory safety limit."""
        search_path = Path(path)
        
        if search_path.is_file() and search_path.suffix == '.py':
            return [str(search_path)]
        
        if search_path.is_dir():
            # Memory-efficient file discovery with limit
            files = []
            for py_file in search_path.rglob('*.py'):
                files.append(str(py_file))
                if len(files) >= max_files:
                    print(f"⚠️  File limit reached: {max_files} files. Use smaller directory or increase limit.")
                    break
            return files
        
        return []
