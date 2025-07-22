"""
Register command implementation for OOPStracker CLI.
"""
from .base import BaseCommand


class RegisterCommand(BaseCommand):
    """Command to register a code snippet."""
    
    async def execute(self) -> int:
        """Execute the register command."""
        records = self.detector.register_code(
            self.args.code,
            function_name=self.args.function_name,
            file_path=self.args.file_path
        )
        
        if records:
            print(f"✅ Registered {len(records)} code units")
            for record in records:
                unit_type = record.metadata.get('type', 'unknown') if record.metadata else 'unknown'
                print(f"   {unit_type}: {record.function_name or 'N/A'} (hash: {record.code_hash[:16]}...)")
        else:
            print("⚠️  No code units found to register")
            
        return 0
        
    @classmethod
    def add_arguments(cls, parser):
        """Add command-specific arguments to the parser."""
        parser.add_argument(
            "code",
            help="Code snippet to register"
        )
        parser.add_argument(
            "--function-name", "-f",
            help="Function name"
        )
        parser.add_argument(
            "--file-path", "-F",
            help="File path"
        )