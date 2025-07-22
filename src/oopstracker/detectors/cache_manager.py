"""
Cache management for AST SimHash detector.

This module handles caching of duplicate detection results
to improve performance for repeated queries.
"""

import logging
from typing import Dict, List, Tuple, Any
from ..models import CodeRecord

logger = logging.getLogger(__name__)


class DetectorCacheManager:
    """Manages caching for duplicate detection results."""
    
    def __init__(self):
        """Initialize cache manager."""
        self._duplicates_cache: Dict[str, List[Tuple[CodeRecord, CodeRecord, float]]] = {}
        self._cache_timestamp = 0
    
    def get_cache_key(self, threshold: float, use_fast_mode: bool, include_trivial: bool, record_count: int) -> str:
        """
        Generate cache key for duplicate detection parameters.
        
        Args:
            threshold: Similarity threshold
            use_fast_mode: Whether fast mode is used
            include_trivial: Whether trivial duplicates are included
            record_count: Total number of records
            
        Returns:
            Cache key string
        """
        return f"{threshold}_{use_fast_mode}_{include_trivial}_{record_count}"
    
    def get_cached_result(
        self,
        cache_key: str,
        current_timestamp: float
    ) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """
        Get cached duplicate detection result if valid.
        
        Args:
            cache_key: Cache key for the query
            current_timestamp: Current data timestamp
            
        Returns:
            Cached result or None if not found/invalid
        """
        if cache_key in self._duplicates_cache and current_timestamp <= self._cache_timestamp:
            logger.info("Using cached duplicate detection results")
            return self._duplicates_cache[cache_key]
        return None
    
    def cache_result(
        self,
        cache_key: str,
        result: List[Tuple[CodeRecord, CodeRecord, float]],
        timestamp: float
    ) -> None:
        """
        Cache duplicate detection result.
        
        Args:
            cache_key: Cache key for the query
            result: Duplicate detection result to cache
            timestamp: Data timestamp
        """
        self._duplicates_cache[cache_key] = result
        self._cache_timestamp = timestamp
        logger.info(f"Cached {len(result)} duplicate pairs")
    
    def clear_cache(self) -> None:
        """Clear all cached results."""
        self._duplicates_cache.clear()
        self._cache_timestamp = 0
        logger.info("Cleared duplicate detection cache")