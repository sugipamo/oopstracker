"""
Refactored CLI using the new architecture without try-catch complexity.
"""

import argparse
import asyncio
from pathlib import Path
from typing import List

from ..domain.services.component_registry import ComponentRegistry
from ..domain.services.unified_detector import UnifiedDetectionService
from ..infrastructure.repositories.unified_repository import UnifiedRepository
from ..application.services.refactored_analysis_service import RefactoredAnalysisService


class RefactoredCLI:
    """Refactored CLI without try-catch blocks."""
    
    def __init__(self):
        self.component_registry = ComponentRegistry()
        self.repository = None
        self.detector = None
        self.analysis_service = None
    
    def initialize_components(self, db_path: str = "oopstracker.db") -> bool:
        """Initialize all components without try-catch."""
        # Create database manager
        db_manager = self.component_registry.create_component(
            "database_manager", 
            db_path=db_path
        )
        
        if not db_manager:
            print("❌ Failed to initialize database manager")
            return False
        
        # Initialize components
        self.repository = UnifiedRepository(db_manager)
        self.detector = UnifiedDetectionService()
        self.analysis_service = RefactoredAnalysisService(self.repository, self.detector)
        
        print(f"✅ Initialized components with database: {db_path}")
        return True
    
    async def run_check_command(self, path: str = ".") -> int:
        """Run check command without try-catch."""
        if not self.initialize_components():
            return 1
        
        # Find Python files
        files = self._find_python_files(path)
        if not files:
            print(f"❌ No Python files found in {path}")
            return 1
        
        print(f"🔍 Analyzing {len(files)} Python files...")
        
        # Perform analysis
        result = self.analysis_service.analyze_files(files)
        
        if not result.success:
            print(f"❌ Analysis failed: {result.error_message}")
            return 1
        
        # Display results
        self._display_results(result)
        return 0
    
    async def run_similar_command(self, source_code: str, algorithm: str = "simhash") -> int:
        """Run similarity check without try-catch."""
        if not self.initialize_components():
            return 1
        
        if not source_code.strip():
            print("❌ Empty source code provided")
            return 1
        
        print(f"🔍 Finding similar code using {algorithm}...")
        
        result = self.analysis_service.find_similar_code(source_code, algorithm)
        
        if not result.success:
            print(f"❌ Similarity check failed: {result.error_message}")
            return 1
        
        if result.duplicates_found > 0:
            print(f"✅ Found {result.processed_records} similar code segments")
        else:
            print("✅ No similar code found")
        
        return 0
    
    def _find_python_files(self, path: str) -> List[str]:
        """Find Python files in path."""
        search_path = Path(path)
        
        if search_path.is_file() and search_path.suffix == '.py':
            return [str(search_path)]
        
        if search_path.is_dir():
            return [str(p) for p in search_path.rglob('*.py')]
        
        return []
    
    def _display_results(self, result):
        """Display analysis results."""
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


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="oopstracker-refactored",
        description="Refactored OOPStracker - Clean Code Analysis"
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Analyze code for duplicates")
    check_parser.add_argument("path", nargs="?", default=".", help="Path to analyze")
    
    # Similar command
    similar_parser = subparsers.add_parser("similar", help="Find similar code")
    similar_parser.add_argument("code", help="Source code to find similarities for")
    similar_parser.add_argument("--algorithm", default="simhash", choices=["simhash", "exact_match"])
    
    return parser


async def main():
    """Main entry point for refactored CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    cli = RefactoredCLI()
    
    if args.command == "check":
        return await cli.run_check_command(args.path)
    elif args.command == "similar":
        return await cli.run_similar_command(args.code, args.algorithm)
    
    return 1


def refactored_cli_main():
    """Synchronous entry point."""
    exit_code = asyncio.run(main())
    exit(exit_code)


if __name__ == "__main__":
    refactored_cli_main()