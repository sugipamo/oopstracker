"""
Database decorators for retry logic and transaction management.
"""

import time
import sqlite3
from functools import wraps
from typing import TypeVar, Callable, Any, Optional
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


def with_retry(max_attempts: int = 3, backoff_factor: float = 1.5) -> Callable:
    """
    Decorator to retry database operations on lock errors.
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Exponential backoff factor for retry delays
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    last_exception = e
                    if "database is locked" in str(e) and attempt < max_attempts - 1:
                        sleep_time = backoff_factor ** attempt
                        logger.warning(
                            f"Database locked, retrying in {sleep_time:.2f}s "
                            f"(attempt {attempt + 1}/{max_attempts})"
                        )
                        time.sleep(sleep_time)
                        continue
                    raise
                except Exception:
                    # Re-raise any non-operational errors immediately
                    raise
                    
            # This should never be reached due to the raise in the loop
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")
            
        return wrapper
    return decorator