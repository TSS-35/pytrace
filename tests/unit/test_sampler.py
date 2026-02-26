"""Tests for span sampling strategies."""
import pytest
import time
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
