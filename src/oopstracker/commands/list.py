"""
List command implementation for OOPStracker CLI.
"""
import json
from .base import BaseCommand


class ListCommand(BaseCommand):
    """Command to list all registered code."""
    
    async def execute(self) -> int:
        """Execute the list command."""
        records = self.detector.get_all_records()
        
        # Sort records
        if self.args.sort_by == "timestamp":
            records.sort(key=lambda r: r.timestamp, reverse=True)
        elif self.args.sort_by == "function":
            records.sort(key=lambda r: r.function_name or "")
        elif self.args.sort_by == "file":
            records.sort(key=lambda r: r.file_path or "")
        elif self.args.sort_by == "hash":
            records.sort(key=lambda r: r.code_hash)
        
        # Apply limit
        if self.args.limit:
            records = records[:self.args.limit]
        
        if self.args.format == "json":
            output = [record.to_dict() for record in records]
            print(json.dumps(output, indent=2, default=str))
        elif self.args.format == "detailed":
            self._display_detailed(records)
        else:  # table format
            self._display_table(records)
            
        return 0
        
    def _display_detailed(self, records):
        """Display records in detailed format."""
        print(f"\n📊 Code Records Summary:")
        print(f"   Total records: {len(self.detector.get_all_records())}")
        if self.args.limit:
            print(f"   Showing: {len(records)} records")
        print(f"   Sorted by: {self.args.sort_by}")
        print("\n" + "=" * 80)
        
        for i, record in enumerate(records, 1):
            print(f"\n📝 Record #{i}")
            print(f"   🔍 Hash: {record.code_hash}")
            print(f"   🏷️  Function: {record.function_name or 'N/A'}")
            print(f"   📁 File: {record.file_path or 'N/A'}")
            print(f"   ⏰ Timestamp: {record.timestamp}")
            if record.metadata:
                print(f"   📋 Type: {record.metadata.get('type', 'N/A')}")
                if 'complexity' in record.metadata:
                    print(f"   🧮 Complexity: {record.metadata['complexity']}")
            if self.args.show_code and record.code_content:
                print(f"   💻 Code:")
                # Show first 10 lines
                lines = record.code_content.split('\n')[:10]
                for line in lines:
                    print(f"      {line}")
                if len(record.code_content.split('\n')) > 10:
                    print(f"      ... ({len(record.code_content.split('\n')) - 10} more lines)")
                    
    def _display_table(self, records):
        """Display records in table format."""
        if not records:
            print("No records found.")
            return
            
        # Print header
        print(f"\n{'Hash':<16} {'Type':<10} {'Function':<30} {'File':<30} {'Timestamp'}")
        print("-" * 100)
        
        # Print records
        for record in records:
            hash_short = record.code_hash[:16] + "..."
            unit_type = record.metadata.get('type', 'unknown')[:10] if record.metadata else 'unknown'
            func_name = (record.function_name or 'N/A')[:30]
            file_path = (record.file_path or 'N/A')
            if len(file_path) > 30:
                file_path = "..." + file_path[-27:]
            timestamp = str(record.timestamp)[:19]
            
            print(f"{hash_short:<16} {unit_type:<10} {func_name:<30} {file_path:<30} {timestamp}")
            
        # Print summary
        print(f"\nShowing {len(records)} of {len(self.detector.get_all_records())} total records")
        
    @classmethod
    def add_arguments(cls, parser):
        """Add command-specific arguments to the parser."""
        parser.add_argument(
            "--format", "-f",
            choices=["table", "json", "detailed"],
            default="table",
            help="Output format (default: table)"
        )
        parser.add_argument(
            "--show-code", "-c",
            action="store_true",
            help="Show code snippets in output"
        )
        parser.add_argument(
            "--limit", "-l",
            type=int,
            help="Limit number of records to show"
        )
        parser.add_argument(
            "--sort-by", "-s",
            choices=["timestamp", "function", "file", "hash"],
            default="timestamp",
            help="Sort records by field (default: timestamp)"
        )