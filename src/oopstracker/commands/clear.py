"""
Clear command implementation for OOPStracker CLI.
"""
import sys
from .base import BaseCommand


class ClearCommand(BaseCommand):
    """Command to clear all registered code."""
    
    async def execute(self) -> int:
        """Execute the clear command."""
        # Get confirmation if not auto-confirmed
        if not self.args.yes:
            print("⚠️  This will delete all registered code records.")
            try:
                response = input("Are you sure? (yes/no): ").strip().lower()
                if response not in ['yes', 'y']:
                    print("❌ Operation cancelled")
                    return 0
            except KeyboardInterrupt:
                print("\n❌ Operation cancelled")
                return 0
                
        # Clear all records
        try:
            self.detector.clear_all_records()
            print("✅ All code records cleared successfully")
            return 0
        except Exception as e:
            print(f"❌ Failed to clear records: {e}")
            return 1
            
    @classmethod
    def add_arguments(cls, parser):
        """Add command-specific arguments to the parser."""
        parser.add_argument(
            "--yes", "-y",
            action="store_true",
            help="Skip confirmation prompt"
        )