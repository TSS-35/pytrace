"""Tests for Config and Tracer sampling integration."""
import pytest
from pytrace.config import Config
from pytrace.tracer import Tracer
from pytrace.sampler import ProbabilitySampler, RateLimitSampler, NoOpSampler
from collector.memory import MemoryCollector


class TestConfigWithSampler:
    """Test Config accepts and stores sampler."""
    
    def test_config_default_sampler(self):
        """Config should have default sampler that always samples."""
        config = Config()
        assert config.sampler is not None
        assert config.sampler.should_sample() is True
    
    def test_config_custom_sampler(self):
        """Config should accept custom sampler."""
        sampler = ProbabilitySampler(0.5)
        config = Config(sampler=sampler)
        
        assert config.sampler is sampler


class TestTracerWithSampling:
    """Test Tracer respects sampling decisions."""
    
    def test_tracer_creates_span_when_sampled(self):
        """Tracer should create span when sampler returns True."""
        sampler = ProbabilitySampler(1.0)  # Always sample
        config = Config(sampler=sampler)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        with tracer.start_span("test_operation"):
            pass
        
        # Should have created span
        assert len(collector.spans) == 1
    
    def test_tracer_skips_span_when_not_sampled(self):
        """Tracer should not create span when sampler returns False."""
        sampler = ProbabilitySampler(0.0)  # Never sample
        config = Config(sampler=sampler)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        with tracer.start_span("test_operation"):
            pass
        
        # Should not have created span
        assert len(collector.spans) == 0
    
    def test_tracer_sampling_reduces_span_count(self):
        """Tracer with sampling should create fewer spans."""
        # Create with 100% sampling
        config_full = Config(sampler=ProbabilitySampler(1.0))
        collector_full = MemoryCollector()
        tracer_full = Tracer(config=config_full, collector=collector_full)
        
        # Create with 50% sampling
        config_half = Config(sampler=ProbabilitySampler(0.5))
        collector_half = MemoryCollector()
        tracer_half = Tracer(config=config_half, collector=collector_half)
        
        # Create same number of spans
        for i in range(100):
            with tracer_full.start_span(f"op_{i}"):
                pass
        
        for i in range(100):
            with tracer_half.start_span(f"op_{i}"):
                pass
        
        # Full should have 100, half should have ~50
        assert len(collector_full.spans) == 100
        assert 30 < len(collector_half.spans) < 70  # Allow variance
    
    def test_tracer_rate_limit_sampler(self):
        """Tracer with rate limit sampler should respect limits."""
        sampler = RateLimitSampler(5)  # 5 spans per second
        config = Config(sampler=sampler)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        # Try to create 10 spans rapidly
        for i in range(10):
            with tracer.start_span(f"op_{i}"):
                pass
        
        # Should only have 5 spans
        assert len(collector.spans) == 5
    
    def test_tracer_respects_sampler_for_child_spans(self):
        """Child spans should follow parent's sampling decision."""
        sampler = ProbabilitySampler(0.0)  # Never sample
        config = Config(sampler=sampler)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        with tracer.start_span("parent"):
            with tracer.start_span("child"):
                pass
        
        # Neither parent nor child should be created
        assert len(collector.spans) == 0


class TestSamplingWithMetrics:
    """Test that sampling doesn't break metrics."""
    
    def test_tracer_metrics_with_sampling(self):
        """Tracer metrics should still work with sampling."""
        sampler = ProbabilitySampler(0.5)
        config = Config(sampler=sampler)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        # Create some spans
        for i in range(10):
            with tracer.start_span("operation"):
                pass
        
        # Span count should match actual stored spans
        assert tracer.span_count() == len(collector.spans)
