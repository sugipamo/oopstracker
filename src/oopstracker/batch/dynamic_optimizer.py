"""
Dynamic batch size optimizer for OOPStracker.
Optimizes batch sizes based on memory usage and LLM token limits.
"""

import psutil
from typing import List, Any
import logging

logger = logging.getLogger(__name__)


class DynamicBatchOptimizer:
    """
    Dynamically calculates optimal batch sizes based on system resources
    and LLM constraints.
    """
    
    def __init__(self, 
                 min_batch_size: int = 5,
                 max_batch_size: int = 50,
                 target_memory_percent: float = 70.0,
                 max_tokens_per_batch: int = 4000):
        """
        Initialize the batch optimizer.
        
        Args:
            min_batch_size: Minimum batch size
            max_batch_size: Maximum batch size
            target_memory_percent: Target memory usage percentage
            max_tokens_per_batch: Maximum tokens for LLM processing
        """
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.target_memory_percent = target_memory_percent
        self.max_tokens_per_batch = max_tokens_per_batch
        
    def calculate_optimal_batch_size(self, 
                                   items: List[Any], 
                                   avg_item_tokens: int = 100) -> int:
        """
        Calculate optimal batch size based on memory and token constraints.
        
        Args:
            items: List of items to batch
            avg_item_tokens: Average tokens per item
            
        Returns:
            Optimal batch size
        """
        # Get available memory
        memory = psutil.virtual_memory()
        available_mb = memory.available / 1024 / 1024
        
        # Estimate memory usage per item (tokens * 4 bytes + overhead)
        estimated_mb_per_item = (avg_item_tokens * 4 + 1000) / 1024 / 1024
        
        # Calculate memory-based maximum batch size
        # Use 30% of available memory for safety
        memory_based_max = int(available_mb * 0.3 / estimated_mb_per_item)
        
        # Calculate token-based maximum batch size
        token_based_max = self.max_tokens_per_batch // avg_item_tokens
        
        # Take the most restrictive constraint
        optimal_size = min(
            self.max_batch_size,
            max(self.min_batch_size, min(memory_based_max, token_based_max))
        )
        
        logger.info(
            f"Batch size calculated: {optimal_size} "
            f"(memory allows: {memory_based_max}, tokens allow: {token_based_max})"
        )
        
        return optimal_size
    
    def get_adaptive_batch_size(self, 
                              current_size: int,
                              success_rate: float,
                              processing_time: float) -> int:
        """
        Adapt batch size based on performance metrics.
        
        Args:
            current_size: Current batch size
            success_rate: Recent success rate (0.0 to 1.0)
            processing_time: Average processing time per batch
            
        Returns:
            Adapted batch size
        """
        # If success rate is low, reduce batch size
        if success_rate < 0.8:
            new_size = max(self.min_batch_size, int(current_size * 0.8))
            logger.info(f"Reducing batch size due to low success rate: {current_size} -> {new_size}")
            return new_size
        
        # If processing is too slow (>30s), reduce size
        if processing_time > 30:
            new_size = max(self.min_batch_size, int(current_size * 0.9))
            logger.info(f"Reducing batch size due to slow processing: {current_size} -> {new_size}")
            return new_size
        
        # If everything is good and processing is fast, try increasing
        if success_rate > 0.95 and processing_time < 10:
            new_size = min(self.max_batch_size, int(current_size * 1.2))
            logger.info(f"Increasing batch size due to good performance: {current_size} -> {new_size}")
            return new_size
        
        # Otherwise, keep current size
        return current_size