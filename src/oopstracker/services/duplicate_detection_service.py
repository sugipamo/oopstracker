"""
Duplicate detection service for OOPStracker.
Handles various duplicate detection strategies and result formatting.
"""

import logging
from typing import List, Optional, Tuple, Dict, Any

from ..models import CodeRecord
from ..progress_reporter import ProgressReporter


class DuplicateDetectionService:
    """Service for detecting and analyzing code duplicates."""
    
    def __init__(self, detector, logger: Optional[logging.Logger] = None):
        """Initialize the duplicate detection service.
        
        Args:
            detector: The AST SimHash detector instance
            logger: Optional logger instance
        """
        self.detector = detector
        self.logger = logger or logging.getLogger(__name__)
        
    async def find_duplicates(self, 
                            enable_detection: bool = False,
                            classification_only: bool = False,
                            disable_detection: bool = False,
                            top_percent: Optional[float] = None,
                            exhaustive: bool = False,
                            include_trivial: bool = False) -> Tuple[List[Tuple[CodeRecord, CodeRecord, float]], str]:
        """Find potential duplicates in the project.
        
        Args:
            enable_detection: Enable duplicate detection
            classification_only: Only run classification, skip duplicate detection
            disable_detection: Disable duplicate detection
            top_percent: Top percentage of duplicates to show
            exhaustive: Use exhaustive search mode
            include_trivial: Include trivial duplicates
            
        Returns:
            Tuple of (duplicates list, threshold display string)
        """
        self.logger.info("Checking all duplicates in project...")
        use_fast_mode = not exhaustive
        
        # Make duplicate detection optional - default OFF for focus on classification
        run_duplicate_detection = enable_detection and not (classification_only or disable_detection)
        
        if run_duplicate_detection:
            # Use dynamic threshold by default (top 3%) if not specified
            if top_percent is None:
                default_top_percent = 3.0  # Default to top 3% of duplicates
                duplicates = self.detector.find_potential_duplicates(
                    threshold=0.7, 
                    use_fast_mode=use_fast_mode, 
                    include_trivial=include_trivial, 
                    silent=False, 
                    top_percent=default_top_percent
                )
                threshold_display = f"dynamic (top {default_top_percent}%)"
            else:
                threshold = 0.7  # More practical threshold for meaningful duplicates
                duplicates = self.detector.find_potential_duplicates(
                    threshold=threshold, 
                    use_fast_mode=use_fast_mode, 
                    include_trivial=include_trivial, 
                    silent=False, 
                    top_percent=top_percent
                )
                threshold_display = f"dynamic (top {top_percent}%)"
        else:
            duplicates = []
            threshold_display = "disabled (focusing on classification)"
            self.logger.info("Prioritizing function classification analysis")
            
        return duplicates, threshold_display
        
    def format_duplicate_summary(self, duplicates_found: List[dict]) -> str:
        """Format duplicate summary for display.
        
        Args:
            duplicates_found: List of duplicate information
            
        Returns:
            Formatted string for display
        """
        if not duplicates_found:
            return ""
            
        lines = [f"\n⚠️  Found {len(duplicates_found)} duplicates:"]
        
        for dup in duplicates_found[:10]:  # Show first 10
            lines.append(f"\n   {dup['type']}: '{dup['name']}' in {dup['file']}")
            for match in dup['matches'][:2]:  # Show first 2 matches
                lines.append(
                    f"      Similar to: {match['name']} in {match['file']} "
                    f"(similarity: {match['similarity']:.3f})"
                )
        
        if len(duplicates_found) > 10:
            lines.append(f"\n   ... and {len(duplicates_found) - 10} more duplicates")
            
        return "\n".join(lines)
        
    def format_duplicate_pairs(self, duplicates: List[Tuple[CodeRecord, CodeRecord, float]], 
                             display_limit: int = 15) -> str:
        """Format duplicate pairs for display.
        
        Args:
            duplicates: List of duplicate pairs
            display_limit: Maximum number of pairs to display
            
        Returns:
            Formatted string for display
        """
        if not duplicates:
            return ""
            
        lines = []
        
        for i, (record1, record2, similarity) in enumerate(duplicates[:display_limit], 1):
            lines.append(self._format_duplicate_pair(record1, record2, similarity, i))
        
        if len(duplicates) > display_limit:
            lines.append(f"\n... and {len(duplicates) - display_limit} more pairs")
            
        return "\n".join(lines)
        
    def _format_duplicate_pair(self, record1: CodeRecord, record2: CodeRecord, 
                              similarity: float, index: int) -> str:
        """Format a single duplicate pair.
        
        Args:
            record1: First code record
            record2: Second code record
            similarity: Similarity score
            index: Display index
            
        Returns:
            Formatted string for the pair
        """
        # Get additional information from code units if available
        unit1 = self.detector.code_units.get(record1.code_hash)
        unit2 = self.detector.code_units.get(record2.code_hash)
        
        # Format file paths with line numbers
        file1 = record1.file_path or "N/A"
        file2 = record2.file_path or "N/A"
        
        if unit1 and unit1.start_line:
            file1 += f":{unit1.start_line}"
        if unit2 and unit2.start_line:
            file2 += f":{unit2.start_line}"
        
        # Get types and complexities
        type1 = unit1.type if unit1 else "unknown"
        type2 = unit2.type if unit2 else "unknown"
        complexity1 = unit1.complexity_score if unit1 else 0
        complexity2 = unit2.complexity_score if unit2 else 0
        
        return (
            f"\n   {index}. [{type1}] {record1.function_name or 'N/A'} ({file1}, complexity: {complexity1})\n"
            f"      ≈ [{type2}] {record2.function_name or 'N/A'} ({file2}, complexity: {complexity2})\n"
            f"      Similarity: {similarity:.3f}"
        )
        
    def get_duplicate_tips(self, duplicates: List[Any], include_trivial: bool, 
                          threshold_display: str) -> str:
        """Get helpful tips based on duplicate detection results.
        
        Args:
            duplicates: List of duplicates found
            include_trivial: Whether trivial duplicates were included
            threshold_display: Current threshold display string
            
        Returns:
            Formatted tips string
        """
        tips = []
        
        if duplicates:
            if not include_trivial:
                tips.append("💡 Use --include-trivial to see all duplicates (including simple classes)")
            tips.append(f"💡 Use --top-percent X to adjust sensitivity ({threshold_display})")
            tips.append("💡 Use --exhaustive for higher accuracy (slower)")
        else:
            tips.append("💡 Try --include-trivial or lower --top-percent for more results")
            
        return "\n".join(tips)