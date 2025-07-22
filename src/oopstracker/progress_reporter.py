"""
Progress reporting utility for OOPStracker.
Provides unified progress display with time-based throttling.
"""

import time
from typing import Optional


class ProgressReporter:
    """Manages progress reporting with time-based throttling."""
    
    def __init__(self, 
                 interval_seconds: float = 5.0,
                 min_items_for_display: int = 50,
                 silent: bool = False,
                 prefix: str = "   "):
        """
        Initialize ProgressReporter.
        
        Args:
            interval_seconds: Minimum seconds between progress updates
            min_items_for_display: Minimum items before showing progress
            silent: If True, suppress all progress output
            prefix: Prefix string for progress messages (for indentation)
        """
        self.interval_seconds = interval_seconds
        self.min_items_for_display = min_items_for_display
        self.silent = silent
        self.prefix = prefix
        self.last_report_time = 0
        self.start_time = time.time()
        
    def should_report(self, current: int, total: int) -> bool:
        """
        Check if progress should be reported.
        
        Args:
            current: Current item number (1-based)
            total: Total number of items
            
        Returns:
            True if progress should be reported
        """
        if self.silent or total < self.min_items_for_display:
            return False
            
        current_time = time.time()
        
        # Always report first item
        if current == 1:
            self.last_report_time = current_time
            return True
            
        # Check time interval
        if current_time - self.last_report_time >= self.interval_seconds:
            self.last_report_time = current_time
            return True
            
        # Always report last item
        if current == total:
            return True
            
        return False
        
    def format_progress(self,
                       current: int,
                       total: int,
                       unit: str = "items",
                       show_percentage: bool = True,
                       show_rate: bool = False) -> str:
        """
        Format progress message.
        
        Args:
            current: Current item number (1-based)
            total: Total number of items
            unit: Unit name (e.g., "files", "records", "pairs")
            show_percentage: Include percentage
            show_rate: Include processing rate
            
        Returns:
            Formatted progress string
        """
        parts = [f"{self.prefix}Processing: {current:,}/{total:,} {unit}"]
        
        if show_percentage:
            percentage = (current / total * 100) if total > 0 else 0
            parts.append(f"({percentage:.1f}%)")
            
        if show_rate and current > 0:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                rate = current / elapsed
                parts.append(f"- {rate:.1f} {unit}/s")
                
                # Estimate remaining time
                if current < total:
                    remaining = (total - current) / rate
                    if remaining < 60:
                        parts.append(f"- ~{remaining:.0f}s remaining")
                    else:
                        minutes = remaining / 60
                        parts.append(f"- ~{minutes:.1f}m remaining")
                        
        return " ".join(parts)
        
    def print_progress(self,
                      current: int,
                      total: int,
                      unit: str = "items",
                      show_percentage: bool = True,
                      show_rate: bool = False) -> None:
        """
        Print progress if appropriate.
        
        Args:
            current: Current item number (1-based)
            total: Total number of items
            unit: Unit name
            show_percentage: Include percentage
            show_rate: Include processing rate
        """
        if self.should_report(current, total):
            message = self.format_progress(current, total, unit, show_percentage, show_rate)
            print(message)
            
    def reset(self) -> None:
        """Reset the reporter for a new progress sequence."""
        self.last_report_time = 0
        self.start_time = time.time()