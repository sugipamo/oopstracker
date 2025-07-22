"""
Duplicate detection analyzer.
"""

from typing import List, Tuple, Any, Optional
from ..base import CommandContext
from ...models import CodeRecord
from .base import BaseAnalyzer, AnalysisResult


class DuplicateAnalyzer(BaseAnalyzer):
    """Analyzer for detecting code duplicates."""
    
    async def analyze(self, **kwargs) -> AnalysisResult:
        """Perform duplicate analysis."""
        use_fast_mode = not self.args.exhaustive
        include_trivial = self.args.include_trivial
        
        # Determine threshold settings
        if self.args.top_percent is None:
            default_top_percent = 3.0
            threshold = 0.7
            top_percent = default_top_percent
            threshold_display = f"dynamic (top {default_top_percent}%)"
        else:
            threshold = getattr(self.args, 'threshold', 
                              getattr(self.args, 'similarity_threshold', 0.7))
            top_percent = self.args.top_percent
            threshold_display = f"dynamic (top {self.args.top_percent}%)"
        
        # Find duplicates
        duplicates = self.detector.find_potential_duplicates(
            threshold=threshold,
            use_fast_mode=use_fast_mode,
            include_trivial=include_trivial,
            silent=False,
            top_percent=top_percent
        )
        
        return AnalysisResult(
            success=True,
            data={
                'duplicates': duplicates,
                'threshold_display': threshold_display,
                'use_fast_mode': use_fast_mode,
                'include_trivial': include_trivial
            },
            summary=f"Found {len(duplicates)} potential duplicate pairs"
        )
    
    def display_results(self, result: AnalysisResult) -> None:
        """Display duplicate analysis results."""
        duplicates = result.data['duplicates']
        threshold_display = result.data['threshold_display']
        
        if duplicates:
            print(f"\n⚠️  Found {len(duplicates)} potential duplicate pairs ({threshold_display}):")
            display_limit = getattr(self.args, 'limit', 15)
            
            for i, (record1, record2, similarity) in enumerate(duplicates[:display_limit], 1):
                print(self._format_duplicate_pair(record1, record2, similarity, i))
            
            if len(duplicates) > display_limit:
                print(f"\n... and {len(duplicates) - display_limit} more pairs")
            
            # Show helpful tips
            if not result.data['include_trivial']:
                print(f"\n💡 Use --include-trivial to see all duplicates (including simple classes)")
            print(f"💡 Use --top-percent X to adjust sensitivity ({threshold_display})")
            print(f"💡 Use --exhaustive for higher accuracy (slower)")
        else:
            print(f"\n✅ No meaningful duplicates found ({threshold_display})!")
            print(f"💡 Try --include-trivial or lower --top-percent for more results")
    
    def _format_duplicate_pair(self, record1: CodeRecord, record2: CodeRecord, 
                              similarity: float, index: int) -> str:
        """Format a duplicate pair for display."""
        def format_name(record):
            name = record.name or record.function_name or 'Unknown'
            type_indicator = '🏛️' if record.type == 'class' else '⚡'
            return f"{type_indicator} {name}"
        
        def truncate_path(path, max_length=60):
            if len(path) <= max_length:
                return path
            parts = path.split('/')
            if len(parts) <= 3:
                return path
            return f".../{'/'.join(parts[-3:])}"
        
        name1 = format_name(record1)
        name2 = format_name(record2)
        file1 = truncate_path(self.format_file_path(record1.file_path))
        file2 = truncate_path(self.format_file_path(record2.file_path))
        
        return f"\n   {index}. {name1} ({file1})\n      ≈ {name2} ({file2})\n      Similarity: {similarity:.3f}"