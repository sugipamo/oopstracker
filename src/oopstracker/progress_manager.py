"""
Progress manager for showing progress at regular intervals.
"""

import time
import sys
from typing import Optional


class ProgressManager:
    """Manage progress display with time-based updates."""
    
    def __init__(self, interval_seconds: float = 10.0):
        """
        Initialize progress manager.
        
        Args:
            interval_seconds: Minimum seconds between progress updates
        """
        self.interval_seconds = interval_seconds
        self.last_update_time: Optional[float] = None
        self.total_items = 0
        self.current_item = 0
        self.current_item_name = ""
        self.start_time: Optional[float] = None
        
    def start(self, total_items: int):
        """Start progress tracking."""
        self.total_items = total_items
        self.current_item = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        
    def update(self, current_item: int, item_name: str = ""):
        """Update progress and display if enough time has passed."""
        self.current_item = current_item
        self.current_item_name = item_name
        
        current_time = time.time()
        
        # Check if enough time has passed since last update
        if self.last_update_time is None or (current_time - self.last_update_time) >= self.interval_seconds:
            self._display_progress()
            self.last_update_time = current_time
            
    def finish(self):
        """Force display final progress."""
        self._display_progress()
        
    def _display_progress(self):
        """Display current progress."""
        if self.total_items == 0:
            return
            
        percentage = (self.current_item / self.total_items) * 100
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        # Estimate remaining time
        if self.current_item > 0:
            avg_time_per_item = elapsed / self.current_item
            remaining_items = self.total_items - self.current_item
            estimated_remaining = avg_time_per_item * remaining_items
            
            # Format time nicely
            if estimated_remaining < 60:
                time_str = f"{int(estimated_remaining)}s"
            else:
                minutes = int(estimated_remaining / 60)
                seconds = int(estimated_remaining % 60)
                time_str = f"{minutes}m {seconds}s"
                
            progress_msg = f"⏳ Progress: {self.current_item}/{self.total_items} ({percentage:.0f}%) - ETA: {time_str}"
        else:
            progress_msg = f"⏳ Progress: {self.current_item}/{self.total_items} ({percentage:.0f}%)"
            
        if self.current_item_name:
            progress_msg += f" - Processing: {self.current_item_name}"
            
        # Print on a new line to avoid interfering with other output
        print(f"\n{progress_msg}")
        
        # Flush to ensure immediate display
        sys.stdout.flush()