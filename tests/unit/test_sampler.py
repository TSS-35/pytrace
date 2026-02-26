"""Tests for span sampling strategies."""
import pytest
import time
import threading
from pytrace.sampler import (
    ProbabilitySampler,
    RateLimitSampler,
    TraceIdSampler,
    NoOpSampler,
    AlwaysSampler
)


class TestProbabilitySampler:
    """Test probability-based sampling."""
    
    def test_probability_sampler_100_percent(self):
        """100% probability should always sample."""
        sampler = ProbabilitySampler(1.0)
        
        for _ in range(10):
            assert sampler.should_sample() is True
    
    def test_probability_sampler_0_percent(self):
        """0% probability should never sample."""
        sampler = ProbabilitySampler(0.0)
        
        for _ in range(10):
            assert sampler.should_sample() is False
    
    def test_probability_sampler_statistical_distribution(self):
        """50% probability should sample roughly 50% of calls."""
        sampler = ProbabilitySampler(0.5)
        samples = [sampler.should_sample() for _ in range(1000)]
        
        # With 1000 samples, we should be between 40-60% (allows variance)
        sample_rate = sum(samples) / len(samples)
        assert 0.4 <= sample_rate <= 0.6
    
    def test_probability_sampler_invalid_probability(self):
        """Sampler should reject invalid probabilities."""
        with pytest.raises(ValueError):
            ProbabilitySampler(-0.1)
        
        with pytest.raises(ValueError):
            ProbabilitySampler(1.5)


class TestRateLimitSampler:
    """Test rate-limiting sampler."""
    
    def test_rate_limit_sampler_allows_under_limit(self):
        """Should allow spans under the rate limit."""
        sampler = RateLimitSampler(10)  # 10 spans per second
        
        # Should allow 10 samples in quick succession
        results = [sampler.should_sample() for _ in range(10)]
        assert all(results)
    
    def test_rate_limit_sampler_rejects_over_limit(self):
        """Should reject spans over the rate limit."""
        sampler = RateLimitSampler(5)  # 5 spans per second
        
        # Sample 6 times rapidly - 6th should be rejected
        results = [sampler.should_sample() for _ in range(6)]
        assert sum(results) == 5
    
    def test_rate_limit_sampler_replenishes_over_time(self):
        """Should replenish capacity after time passes."""
        sampler = RateLimitSampler(2)  # 2 spans per second
        
        # Use up capacity
        results1 = [sampler.should_sample() for _ in range(2)]
        assert sum(results1) == 2
        
        # Next sample should be rejected
        assert sampler.should_sample() is False
        
        # Wait for token to replenish (more than 500ms for 2/sec)
        time.sleep(0.6)
        
        # Should allow next sample
        assert sampler.should_sample() is True
    
    def test_rate_limit_sampler_invalid_rate(self):
        """Should reject invalid rates."""
        with pytest.raises(ValueError):
            RateLimitSampler(0)
        
        with pytest.raises(ValueError):
            RateLimitSampler(-1)


class TestRateLimitSamplerThreadSafety:
    """Test thread-safety of RateLimitSampler."""
    
    def test_rate_limit_sampler_thread_safe(self):
        """RateLimitSampler should be thread-safe with concurrent access."""
        sampler = RateLimitSampler(20)  # 20 spans per second
        results = []
        
        def sample_many_times():
            """Worker thread that calls should_sample multiple times."""
            for _ in range(50):
                results.append(sampler.should_sample())
        
        # Create multiple threads that all access sampler concurrently
        threads = [threading.Thread(target=sample_many_times) for _ in range(4)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have made 200 total calls (50 * 4 threads)
        assert len(results) == 200
        
        # Should have respect rate limit approximately
        # With 20 spans/sec limit, rapid fire should get ~20 sampled
        # (may be slightly more due to timing, but not 200)
        sampled_count = sum(results)
        assert 15 < sampled_count < 40  # Allow some variance
    
    def test_rate_limit_sampler_no_race_condition(self):
        """RateLimitSampler should not have race conditions on token state."""
        sampler = RateLimitSampler(50)  # 50 spans per second
        sampled_count = 0
        lock = threading.Lock()
        
        def concurrent_sampling():
            """Worker that samples many times."""
            nonlocal sampled_count
            local_count = 0
            for _ in range(100):
                if sampler.should_sample():
                    local_count += 1
            
            with lock:
                sampled_count += local_count
        
        # Hammer with multiple threads
        threads = [threading.Thread(target=concurrent_sampling) for _ in range(10)]
        
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        elapsed = time.time() - start_time
        
        # Should have sampled approximately rate_limit * elapsed
        # But the rapid-fire nature means we'll hit the initial token bucket
        # Just verify that the sampled count is reasonable (not all 1000)
        # and that threads are safe (no exceptions or crashes)
        
        # Should get initial bucket (50) plus refills during execution
        # With threads racing, expect 50-150 samples
        assert 40 < sampled_count < 200, \
            f"Sampled {sampled_count} spans, expected 40-200 (thread-safe behavior)"



class TestTraceIdSampler:
    """Test trace-id based sampling (entire trace or nothing)."""
    
    def test_trace_id_sampler_100_percent(self):
        """100% probability should sample all traces."""
        sampler = TraceIdSampler(1.0)
        
        # All trace IDs should be sampled
        for trace_id in ["trace1", "trace2", "trace3"]:
            assert sampler.should_sample(trace_id) is True
    
    def test_trace_id_sampler_0_percent(self):
        """0% probability should sample no traces."""
        sampler = TraceIdSampler(0.0)
        
        # No trace IDs should be sampled
        for trace_id in ["trace1", "trace2", "trace3"]:
            assert sampler.should_sample(trace_id) is False
    
    def test_trace_id_sampler_deterministic(self):
        """Same trace ID should always get same decision."""
        sampler = TraceIdSampler(0.5)
        trace_id = "consistent-trace-123"
        
        # Call multiple times with same trace ID
        results = [sampler.should_sample(trace_id) for _ in range(10)]
        
        # All results should be the same
        assert len(set(results)) == 1
    
    def test_trace_id_sampler_statistical_distribution(self):
        """50% probability should sample roughly 50% of traces."""
        sampler = TraceIdSampler(0.5)
        
        # Test many different trace IDs
        trace_ids = [f"trace-{i}" for i in range(1000)]
        samples = [sampler.should_sample(trace_id) for trace_id in trace_ids]
        
        # Should be roughly 50% sampled
        sample_rate = sum(samples) / len(samples)
        assert 0.4 <= sample_rate <= 0.6
    
    def test_trace_id_sampler_invalid_probability(self):
        """Should reject invalid probabilities."""
        with pytest.raises(ValueError):
            TraceIdSampler(-0.1)
        
        with pytest.raises(ValueError):
            TraceIdSampler(1.5)


class TestNoOpSampler:
    """Test no-op sampler (always samples)."""
    
    def test_noop_sampler_always_samples(self):
        """NoOp sampler should always sample."""
        sampler = NoOpSampler()
        
        for _ in range(10):
            assert sampler.should_sample() is True


class TestAlwaysSampler:
    """Test always sampler (alternative name for no-op)."""
    
    def test_always_sampler_always_samples(self):
        """AlwaysSampler should always sample."""
        sampler = AlwaysSampler()
        
        for _ in range(10):
            assert sampler.should_sample() is True


class TestSamplerWithTraceContext:
    """Test samplers with trace context (if applicable)."""
    
    def test_sampler_interface_consistency(self):
        """All samplers should have consistent interface."""
        samplers = [
            ProbabilitySampler(0.5),
            RateLimitSampler(10),
            TraceIdSampler(0.5),
            NoOpSampler(),
            AlwaysSampler()
        ]
        
        for sampler in samplers:
            # All should have should_sample method
            assert hasattr(sampler, 'should_sample')
            assert callable(sampler.should_sample)    
    def test_requires_trace_id_method_exists(self):
        """All samplers should have requires_trace_id method."""
        samplers = [
            ProbabilitySampler(0.5),
            RateLimitSampler(10),
            TraceIdSampler(0.5),
            NoOpSampler(),
            AlwaysSampler()
        ]
        
        for sampler in samplers:
            assert hasattr(sampler, 'requires_trace_id')
            assert callable(sampler.requires_trace_id)
    
    def test_trace_id_sampler_requires_trace_id(self):
        """TraceIdSampler should indicate it requires trace_id."""
        sampler = TraceIdSampler(0.5)
        assert sampler.requires_trace_id() is True
    
    def test_other_samplers_dont_require_trace_id(self):
        """Other samplers should not require trace_id."""
        samplers = [
            ProbabilitySampler(0.5),
            RateLimitSampler(10),
            NoOpSampler(),
            AlwaysSampler()
        ]
        
        for sampler in samplers:
            assert sampler.requires_trace_id() is False
    
    def test_robust_sampler_detection(self):
        """Should be able to detect sampler type without fragile class name checks."""
        # Create samplers with different names to ensure we don't rely on class names
        trace_id_sampler = TraceIdSampler(0.5)
        prob_sampler = ProbabilitySampler(0.5)
        
        # Use requires_trace_id() instead of class name comparison
        # This is more robust and extensible
        if trace_id_sampler.requires_trace_id():
            # TraceIdSampler needs trace_id
            assert trace_id_sampler.should_sample("trace-123") is not None
        
        if not prob_sampler.requires_trace_id():
            # ProbabilitySampler doesn't need trace_id
            assert prob_sampler.should_sample() is not None