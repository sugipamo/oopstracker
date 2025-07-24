"""
Adaptive rate limiter for API calls.
Dynamically adjusts request rates based on success/failure patterns.
"""

import time
from dataclasses import dataclass
from typing import Optional
import logging
import threading

logger = logging.getLogger(__name__)


@dataclass
class RateLimitState:
    """State tracking for rate limiting."""
    current_rps: float = 10.0
    last_request_time: float = 0.0
    consecutive_successes: int = 0
    consecutive_failures: int = 0


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts request rates based on API responses.
    Thread-safe implementation for concurrent usage.
    """
    
    def __init__(self, 
                 initial_rps: float = 10.0, 
                 min_rps: float = 1.0, 
                 max_rps: float = 50.0):
        """
        Initialize the rate limiter.
        
        Args:
            initial_rps: Initial requests per second
            min_rps: Minimum requests per second
            max_rps: Maximum requests per second
        """
        self.state = RateLimitState(current_rps=initial_rps)
        self.min_rps = min_rps
        self.max_rps = max_rps
        self._lock = threading.Lock()
        
    def acquire(self) -> None:
        """
        Acquire permission to make a request.
        Blocks if necessary to maintain rate limit.
        """
        with self._lock:
            current_time = time.time()
            time_since_last = current_time - self.state.last_request_time
            min_interval = 1.0 / self.state.current_rps
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                logger.debug(f"Rate limiting: sleeping {sleep_time:.3f}s")
                time.sleep(sleep_time)
                
            self.state.last_request_time = time.time()
        
    def report_success(self) -> None:
        """
        Report a successful API call.
        May increase rate limit if consistently successful.
        """
        with self._lock:
            self.state.consecutive_successes += 1
            self.state.consecutive_failures = 0
            
            # Increase rate after 10 consecutive successes
            if self.state.consecutive_successes >= 10:
                old_rps = self.state.current_rps
                self.state.current_rps = min(self.state.current_rps * 1.2, self.max_rps)
                logger.info(
                    f"Rate limit increased: {old_rps:.1f} -> {self.state.current_rps:.1f} RPS"
                )
                self.state.consecutive_successes = 0
            
    def report_failure(self, is_rate_limit: bool = False) -> None:
        """
        Report a failed API call.
        
        Args:
            is_rate_limit: Whether the failure was due to rate limiting
        """
        with self._lock:
            self.state.consecutive_failures += 1
            self.state.consecutive_successes = 0
            
            # Decrease rate more aggressively for rate limit errors
            if is_rate_limit:
                old_rps = self.state.current_rps
                self.state.current_rps = max(self.state.current_rps * 0.5, self.min_rps)
                logger.warning(
                    f"Rate limit hit! Decreased: {old_rps:.1f} -> {self.state.current_rps:.1f} RPS"
                )
                self.state.consecutive_failures = 0
            # Decrease rate after 2 consecutive failures
            elif self.state.consecutive_failures >= 2:
                old_rps = self.state.current_rps
                self.state.current_rps = max(self.state.current_rps * 0.8, self.min_rps)
                logger.warning(
                    f"Rate limit decreased: {old_rps:.1f} -> {self.state.current_rps:.1f} RPS"
                )
                self.state.consecutive_failures = 0
                
    def get_current_rps(self) -> float:
        """Get the current requests per second limit."""
        with self._lock:
            return self.state.current_rps
            
    def reset(self) -> None:
        """Reset the rate limiter to initial state."""
        with self._lock:
            self.state = RateLimitState(current_rps=10.0)
            logger.info("Rate limiter reset to initial state")