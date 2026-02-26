"""Span sampling strategies for production tracing."""
import hashlib
import random
import threading
import time
from abc import ABC, abstractmethod
from typing import Optional


class Sampler(ABC):
    """Base class for sampling strategies."""
    
    @abstractmethod
    def should_sample(self, trace_id: Optional[str] = None) -> bool:
        """Determine if a span should be sampled.
        
        Args:
            trace_id: Optional trace ID for trace-level sampling decisions
            
        Returns:
            True if span should be collected, False otherwise
        """
        pass
    
    def requires_trace_id(self) -> bool:
        """Indicate whether this sampler requires a trace_id parameter.
        
        Returns:
            True if should_sample() requires a trace_id argument
            False if should_sample() can be called without trace_id
        """
        return False


class NoOpSampler(Sampler):
    """Sampler that always samples (no-op, default behavior)."""
    
    def should_sample(self, trace_id: Optional[str] = None) -> bool:
        """Always return True - sample everything."""
        return True


class AlwaysSampler(Sampler):
    """Sampler that always samples (same as NoOpSampler)."""
    
    def should_sample(self, trace_id: Optional[str] = None) -> bool:
        """Always return True - sample everything."""
        return True


class ProbabilitySampler(Sampler):
    """Sample a percentage of spans based on probability.
    
    Example:
        sampler = ProbabilitySampler(0.1)  # Sample 10% of spans
    """
    
    def __init__(self, probability: float):
        """Initialize with sampling probability.
        
        Args:
            probability: Sampling probability (0.0 to 1.0)
            
        Raises:
            ValueError: If probability is not between 0 and 1
        """
        if not (0.0 <= probability <= 1.0):
            raise ValueError(f"Probability must be between 0 and 1, got {probability}")
        
        self.probability = probability
    
    def should_sample(self, trace_id: Optional[str] = None) -> bool:
        """Return True based on configured probability."""
        return random.random() < self.probability


class TraceIdSampler(Sampler):
    """Sample entire traces based on trace ID hash.
    
    Same trace ID always gets same sampling decision (deterministic).
    Uses SHA256 for stable hashing across processes in distributed systems.
    Useful for keeping complete traces together.
    
    Example:
        sampler = TraceIdSampler(0.1)  # Sample 10% of traces
    """
    
    def __init__(self, probability: float):
        """Initialize with sampling probability.
        
        Args:
            probability: Sampling probability (0.0 to 1.0)
            
        Raises:
            ValueError: If probability is not between 0 and 1
        """
        if not (0.0 <= probability <= 1.0):
            raise ValueError(f"Probability must be between 0 and 1, got {probability}")
        
        self.probability = probability
    
    def should_sample(self, trace_id: Optional[str] = None) -> bool:
        """Return sampling decision based on trace ID hash.
        
        Uses SHA256 for stable hashing that's consistent across processes.
        This ensures the same trace_id produces the same sampling decision
        across all services in a distributed system.
        
        Args:
            trace_id: Trace ID to hash for deterministic decision
            
        Returns:
            Deterministic True/False based on trace_id hash
        """
        if trace_id is None:
            raise ValueError("TraceIdSampler requires trace_id")
        
        # Use SHA256 for stable hash across processes and Python versions
        # (Python's built-in hash() uses randomization and is not stable)
        hash_bytes = hashlib.sha256(trace_id.encode()).digest()
        # Take first 4 bytes as unsigned integer
        hash_value = int.from_bytes(hash_bytes[:4], byteorder='big') % 10000
        threshold = int(self.probability * 10000)
        
        return hash_value < threshold
    
    def requires_trace_id(self) -> bool:
        """TraceIdSampler requires trace_id for deterministic decisions."""
        return True


class RateLimitSampler(Sampler):
    """Limit spans to a maximum rate (spans per second).
    
    Uses token bucket algorithm for smooth rate limiting.
    Thread-safe: uses a lock to protect shared state (tokens and last_refill).
    Safe for use in multi-threaded applications.
    
    Example:
        sampler = RateLimitSampler(100)  # Max 100 spans per second
    """
    
    def __init__(self, max_spans_per_second: int):
        """Initialize with rate limit.
        
        Args:
            max_spans_per_second: Maximum spans per second
            
        Raises:
            ValueError: If rate is not positive
        """
        if max_spans_per_second <= 0:
            raise ValueError(f"Rate must be positive, got {max_spans_per_second}")
        
        self.max_spans_per_second = max_spans_per_second
        self.tokens = max_spans_per_second  # Start with full capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()  # Protect shared state
    
    def should_sample(self, trace_id: Optional[str] = None) -> bool:
        """Check if span is within rate limit using token bucket.
        
        Thread-safe implementation using a lock to prevent race conditions
        in the token bucket state.
        
        Returns:
            True if within rate limit, False otherwise
        """
        with self._lock:
            current_time = time.time()
            time_passed = current_time - self.last_refill
            
            # Add tokens based on time passed
            # Each second, we add max_spans_per_second tokens
            tokens_to_add = time_passed * self.max_spans_per_second
            self.tokens = min(
                self.max_spans_per_second,
                self.tokens + tokens_to_add
            )
            self.last_refill = current_time
            
            # Check if we have tokens
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            
            return False
