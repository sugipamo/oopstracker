"""
Analyze command implementation for OOPStracker CLI.
"""
from .base import BaseCommand


class AnalyzeCommand(BaseCommand):
    """Command to analyze code structure (AST mode only)."""
    
    async def execute(self) -> int:
        """Execute the analyze command."""
        # Analyze code structure
        print(f"🔍 Analyzing code structure...")
        
        analysis = self.detector.analyze_code(
            self.args.code,
            file_path=self.args.file_path
        )
        
        if analysis:
            print(f"\n📊 AST Analysis Results:")
            print(f"   SimHash: {analysis.simhash}")
            print(f"   Type: {analysis.type}")
            print(f"   Complexity: {analysis.complexity}")
            
            if analysis.imports:
                print(f"\n📦 Imports ({len(analysis.imports)}):")
                for imp in analysis.imports[:10]:
                    print(f"   - {imp}")
                if len(analysis.imports) > 10:
                    print(f"   ... and {len(analysis.imports) - 10} more")
                    
            if analysis.function_calls:
                print(f"\n📞 Function Calls ({len(analysis.function_calls)}):")
                call_counts = {}
                for call in analysis.function_calls:
                    call_counts[call] = call_counts.get(call, 0) + 1
                
                sorted_calls = sorted(call_counts.items(), key=lambda x: x[1], reverse=True)
                for call, count in sorted_calls[:10]:
                    print(f"   - {call} ({count} times)")
                if len(sorted_calls) > 10:
                    print(f"   ... and {len(sorted_calls) - 10} more unique calls")
                    
            if analysis.classes:
                print(f"\n🏫 Classes ({len(analysis.classes)}):")
                for cls in analysis.classes:
                    print(f"   - {cls}")
                    
            if analysis.functions:
                print(f"\n⚙️  Functions ({len(analysis.functions)}):")
                for func in analysis.functions:
                    print(f"   - {func}")
                    
            print(f"\n📦 Metadata:")
            print(f"   Lines of code: {analysis.metadata.get('lines', 'N/A')}")
            print(f"   AST nodes: {analysis.metadata.get('ast_nodes', 'N/A')}")
            
            # Show similar code if any
            result = self.detector.find_similar(
                self.args.code,
                function_name=None,
                file_path=self.args.file_path
            )
            
            if result.is_duplicate and result.matched_records:
                print(f"\n⚠️  Found {len(result.matched_records)} similar code units:")
                for i, match in enumerate(result.matched_records[:5], 1):
                    print(f"\n   {i}. {match.function_name or 'N/A'} in {match.file_path or 'N/A'}")
                    print(f"      Similarity: {match.similarity_score:.3f}")
                    print(f"      Hash: {match.code_hash[:16]}...")
                    
                if len(result.matched_records) > 5:
                    print(f"\n   ... and {len(result.matched_records) - 5} more matches")
            else:
                print(f"\n✅ No similar code found in the database")
        else:
            print("❌ Failed to analyze code")
            print("   Please check the code syntax")
            
        return 0
        
    @classmethod
    def add_arguments(cls, parser):
        """Add command-specific arguments to the parser."""
        parser.add_argument(
            "code",
            help="Code to analyze"
        )
        parser.add_argument(
            "--file-path", "-F",
            help="File path for context"
        )