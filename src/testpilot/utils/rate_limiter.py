"""
Rate Limiter Utility for TestPilot

Implements token bucket algorithm for rate limiting HTTP requests.
Supports per-host rate limiting and global rate limiting.
Thread-safe implementation for concurrent request handling.
"""

import threading
import time
from typing import Dict, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter implementation.

    Allows smooth rate limiting with configurable requests per second.
    Supports per-host tracking or global rate limiting.
    """

    def __init__(self,
                 default_rate: float = 10.0,
                 per_host: bool = False,
                 burst_size: Optional[int] = None):
        """
        Initialize rate limiter.

        Args:
            default_rate: Default requests per second (float)
            per_host: If True, maintain separate limits per host
            burst_size: Maximum burst tokens (defaults to rate, not rate * 2)
        """
        self.default_rate = max(0.1, default_rate)  # Minimum 0.1 reqs/sec
        self.per_host = per_host
        # For stricter rate limiting, start with burst_size = rate (not rate * 2)
        self.burst_size = burst_size or max(1, int(self.default_rate))

        # Thread safety
        self._lock = threading.Lock()

        # Per-host tracking: {host: {'tokens': float, 'last_update': float, 'rate': float}}
        self._host_buckets: Dict[str, Dict] = {}

        # Global bucket for non-per-host mode
        # Start with 1 token to allow first request immediately, but enforce rate after that
        self._global_bucket = {
            'tokens': 1.0,
            'last_update': time.time(),
            'rate': self.default_rate
        }

        logger.info(f"RateLimiter initialized: rate={self.default_rate} reqs/sec, "
                   f"per_host={per_host}, burst_size={self.burst_size}")

    def set_rate(self, rate: float, host: Optional[str] = None) -> None:
        """
        Update rate for specific host or globally.

        Args:
            rate: New requests per second rate
            host: Host to update (None for global)
        """
        rate = max(0.1, rate)  # Minimum rate

        with self._lock:
            if self.per_host and host:
                if host not in self._host_buckets:
                    self._init_bucket_for_host(host)
                self._host_buckets[host]['rate'] = rate
                logger.debug(f"Rate updated for {host}: {rate} reqs/sec")
            else:
                self._global_bucket['rate'] = rate
                self.default_rate = rate
                logger.debug(f"Global rate updated: {rate} reqs/sec")

    def acquire(self, host: Optional[str] = None, tokens: int = 1) -> float:
        """
        Acquire tokens for request execution.

        Args:
            host: Target host (used if per_host=True)
            tokens: Number of tokens to acquire (default: 1)

        Returns:
            float: Delay in seconds needed to maintain rate (0 if no delay needed)
        """
        with self._lock:
            bucket = self._get_bucket(host)
            current_time = time.time()

            # Refill tokens based on elapsed time
            elapsed = current_time - bucket['last_update']
            bucket['tokens'] = min(
                self.burst_size,
                bucket['tokens'] + elapsed * bucket['rate']
            )
            bucket['last_update'] = current_time

            # Check if we have enough tokens
            if bucket['tokens'] >= tokens:
                # Consume tokens immediately
                bucket['tokens'] -= tokens
                logger.debug(f"Tokens acquired for {host or 'global'}: "
                           f"remaining={bucket['tokens']:.2f}")
                return 0.0
            else:
                # Calculate delay needed
                deficit = tokens - bucket['tokens']
                delay = deficit / bucket['rate']

                # Consume available tokens
                bucket['tokens'] = 0

                logger.debug(f"Rate limit delay for {host or 'global'}: "
                           f"{delay:.2f}s (deficit={deficit:.2f} tokens)")
                return delay

    def get_status(self, host: Optional[str] = None) -> Dict:
        """
        Get current rate limiter status.

        Args:
            host: Host to check (None for global)

        Returns:
            Dict with status information
        """
        with self._lock:
            bucket = self._get_bucket(host)
            current_time = time.time()

            # Update tokens before reporting
            elapsed = current_time - bucket['last_update']
            current_tokens = min(
                self.burst_size,
                bucket['tokens'] + elapsed * bucket['rate']
            )

            return {
                'host': host or 'global',
                'rate': bucket['rate'],
                'tokens': current_tokens,
                'burst_size': self.burst_size,
                'per_host_mode': self.per_host
            }

    def reset(self, host: Optional[str] = None) -> None:
        """
        Reset rate limiter state.

        Args:
            host: Host to reset (None for all)
        """
        with self._lock:
            if host and self.per_host:
                if host in self._host_buckets:
                    self._init_bucket_for_host(host)
                    logger.debug(f"Rate limiter reset for {host}")
            else:
                # Reset all
                self._host_buckets.clear()
                self._global_bucket = {
                    'tokens': 1.0,
                    'last_update': time.time(),
                    'rate': self.default_rate
                }
                logger.debug("Rate limiter reset (all)")

    def _get_bucket(self, host: Optional[str] = None) -> Dict:
        """Get the appropriate bucket for host or global."""
        if self.per_host and host:
            if host not in self._host_buckets:
                self._init_bucket_for_host(host)
            return self._host_buckets[host]
        else:
            return self._global_bucket

    def _init_bucket_for_host(self, host: str) -> None:
        """Initialize bucket for new host."""
        self._host_buckets[host] = {
            'tokens': 1.0,  # Start with 1 token like global bucket
            'last_update': time.time(),
            'rate': self.default_rate
        }
        logger.debug(f"Initialized rate bucket for {host}")


def create_rate_limiter_from_config(config: Dict) -> Optional[RateLimiter]:
    """
    Create RateLimiter from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        RateLimiter instance or None if disabled
    """
    rate_config = config.get('rate_limiting', {})

    if not rate_config.get('enabled', False):
        logger.debug("Rate limiting disabled in config")
        return None

    default_rate = rate_config.get('default_reqs_per_sec', 10.0)
    per_host = rate_config.get('per_host', False)
    burst_size = rate_config.get('burst_size')

    logger.info(f"Creating rate limiter from config: rate={default_rate}, per_host={per_host}")

    return RateLimiter(
        default_rate=default_rate,
        per_host=per_host,
        burst_size=burst_size
    )


def parse_excel_rate_limit(step_data: Dict, default_rate: Optional[float] = None) -> Optional[float]:
    """
    Parse rate limit from Excel step data.

    Args:
        step_data: Step other_fields dictionary
        default_rate: Fallback rate if not specified

    Returns:
        Parsed rate or default_rate or None
    """
    # Check various possible column names (case insensitive)
    rate_keys = ['reqs_sec', 'Reqs_Sec', 'reqs_per_sec', 'Reqs_Per_Sec', 'rate_limit']

    for key in rate_keys:
        if key in step_data:
            try:
                rate = float(step_data[key])
                if rate > 0:
                    logger.debug(f"Parsed Excel rate limit: {rate} reqs/sec from column '{key}'")
                    return rate
                else:
                    logger.warning(f"Invalid rate limit in Excel: {rate} (must be > 0)")
            except (ValueError, TypeError):
                logger.warning(f"Could not parse rate limit from Excel column '{key}': {step_data[key]}")

    return default_rate