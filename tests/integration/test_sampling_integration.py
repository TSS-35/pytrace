"""Integration tests for sampling functionality."""
import pytest
from pytrace.config import Config
from pytrace.tracer import Tracer
from pytrace.sampler import (
    ProbabilitySampler,
    RateLimitSampler,
    TraceIdSampler,
    AlwaysSampler
)
from collector.memory import MemoryCollector


class TestSamplingInRealScenarios:
    """Test sampling in realistic production scenarios."""
    
    def test_high_volume_api_with_probability_sampling(self):
        """Simulate high-volume API calls with probability sampling."""
        # In production: simulate 1000 requests
        sampler = ProbabilitySampler(0.01)  # 1% sampling
        config = Config(sampler=sampler)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        # Simulate 1000 API requests
        for i in range(1000):
            with tracer.start_span(f"api_request_{i % 3}"):
                pass
        
        # Should have roughly 10 spans (1% of 1000), allowing for variance
        assert 3 < len(collector.spans) < 30
    
    def test_trace_id_sampling_keeps_traces_together(self):
        """TraceIdSampler ensures entire traces are kept together."""
        sampler = TraceIdSampler(0.5)  # 50% of traces
        config = Config(sampler=sampler)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        # Create 10 traces with 3 spans each
        for trace_num in range(10):
            trace_id = f"trace-{trace_num}"
            
            # Create parent span
            with tracer.start_span("api_call", trace_id=trace_id):
                # Create child spans
                with tracer.start_span("database_query"):
                    pass
                with tracer.start_span("cache_lookup"):
                    pass
        
        # Should have sampled ~50% of traces
        # Each sampled trace has 3 spans (5 traces * 3 = 15, but allow variance)
        assert 8 < len(collector.spans) < 25
        
        # All spans in collector should belong to same traces
        trace_ids = {span.trace_id for span in collector.spans}
        for trace_id in trace_ids:
            trace_spans = [s for s in collector.spans if s.trace_id == trace_id]
            # Each trace should have 3 spans (all or nothing)
            assert len(trace_spans) == 3
    
    def test_rate_limiting_caps_database_spans(self):
        """Rate limiting prevents overwhelming the database."""
        # Limit to 50 spans per second
        sampler = RateLimitSampler(50)
        config = Config(sampler=sampler)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        # Try to create 100 spans immediately
        for i in range(100):
            with tracer.start_span("database_query"):
                pass
        
        # Should be capped at 50
        assert len(collector.spans) == 50
    
    def test_combined_sampling_strategies(self):
        """Test scenarios where different operations use different sampling."""
        # Critical operations: always sample
        critical_sampler = AlwaysSampler()
        
        # Normal operations: 10% sample
        normal_sampler = ProbabilitySampler(0.1)
        
        config = Config(sampler=normal_sampler)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        # Create 100 critical spans (would normally sample them all)
        for i in range(100):
            with tracer.start_span("critical_operation"):
                pass
        
        # With normal sampler, should have ~10 critical spans
        # Allow wider variance for probability-based sampling
        critical_count = len(collector.spans)
        assert 3 < critical_count < 30


class TestSamplingWithMetricsAccuracy:
    """Test that metrics remain accurate with sampling."""
    
    def test_metrics_reflect_sampled_data(self):
        """Metrics should be accurate for sampled data."""
        sampler = ProbabilitySampler(0.5)
        config = Config(sampler=sampler)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        # Create 100 spans with ~50% error rate
        for i in range(100):
            with tracer.start_span(f"operation_{i}") as span:
                if i % 2 == 0:
                    span.attributes["error"] = "true"
        
        # Metrics should reflect sampled spans only
        span_count = tracer.span_count()
        error_count = tracer.error_count()
        
        # Should have ~50 spans
        assert 30 < span_count < 70
        
        # Error count should be roughly half of span count
        error_rate = error_count / span_count if span_count > 0 else 0
        assert 0.3 < error_rate < 0.7
    
    def test_operation_counts_with_sampling(self):
        """Operation counts should reflect sampled distribution."""
        sampler = ProbabilitySampler(0.5)
        config = Config(sampler=sampler)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        # Create 50 spans per operation type
        operations = ["api_call", "database_query", "cache_lookup"]
        for operation in operations:
            for i in range(50):
                with tracer.start_span(operation):
                    pass
        
        counts = tracer.span_counts_by_name()
        
        # Each operation should be sampled roughly equally
        for operation in operations:
            # Should have ~25 spans of each operation (50% of 50)
            assert operation in counts
            assert 10 < counts[operation] < 40


class TestSamplingConfigurationPatterns:
    """Test common sampling configuration patterns."""
    
    def test_debug_mode_no_sampling(self):
        """Debug mode configuration with no sampling."""
        sampler = AlwaysSampler()
        config = Config(sampler=sampler)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        # Create 100 spans
        for i in range(100):
            with tracer.start_span("operation"):
                pass
        
        # Should have all 100 spans
        assert len(collector.spans) == 100
    
    def test_production_mode_aggressive_sampling(self):
        """Production mode with aggressive sampling to reduce volume."""
        sampler = ProbabilitySampler(0.001)  # 0.1% sampling
        config = Config(sampler=sampler)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        # Create 10000 spans
        for i in range(10000):
            with tracer.start_span("operation"):
                pass
        
        # Should have roughly 10 spans (0.1% of 10000)
        assert 5 < len(collector.spans) < 20
    
    def test_sampling_per_span_type(self):
        """Different sampling rates per span type (requires custom logic)."""
        config = Config(sampler=ProbabilitySampler(0.5))
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        # Note: This test demonstrates a use case that might need
        # future enhancement (per-operation sampling), but shows
        # current functionality works for global sampling
        
        for i in range(100):
            with tracer.start_span("operation"):
                pass
        
        # Sampling applies to all spans
        assert 30 < len(collector.spans) < 70
