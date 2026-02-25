"""Integration tests for end-to-end tracing flow."""
import pytest
import time
from pytrace.tracer import Tracer
from pytrace.query import Query
from collector.memory import MemoryCollector


class TestEndToEndTracingFlow:
    """Test complete tracing lifecycle from span creation to querying."""
    
    def test_simple_span_creation_to_query(self):
        """Verify basic span creation and querying."""
        collector = MemoryCollector()
        tracer = Tracer(collector=collector)
        
        # Create span
        span = tracer.start_span("database_query")
        span.add_event("query_started")
        time.sleep(0.01)
        span.finish()
        
        # Query back
        results = Query(collector).by_name("database_query").execute()
        
        assert len(results) == 1
        assert results[0].duration > 10  # At least 10ms
        assert len(results[0].events) == 1
    
    def test_nested_spans_hierarchy(self):
        """Verify parent-child relationships maintained through lifecycle."""
        collector = MemoryCollector()
        tracer = Tracer(collector=collector)
        
        # Create parent with children
        with tracer.start_span("parent", trace_id="trace_1") as parent:
            with tracer.start_span("child_1") as child1:
                child1.add_event("work_1")
                child1.finish()
            
            with tracer.start_span("child_2") as child2:
                child2.add_event("work_2")
                child2.finish()
        
        # Verify hierarchy in collected spans
        parent_results = Query(collector).by_name("parent").execute()
        child1_results = Query(collector).by_name("child_1").execute()
        child2_results = Query(collector).by_name("child_2").execute()
        
        assert len(parent_results) == 1
        assert len(child1_results) == 1
        assert len(child2_results) == 1
        
        assert child1_results[0].parent_id == parent_results[0].span_id
        assert child2_results[0].parent_id == parent_results[0].span_id
        assert child1_results[0].trace_id == child2_results[0].trace_id == parent_results[0].trace_id
    
    def test_multiple_traces_isolated(self):
        """Verify multiple traces don't interfere with each other."""
        collector = MemoryCollector()
        tracer = Tracer(collector=collector)
        
        # Create trace 1
        with tracer.start_span("op1", trace_id="trace_1"):
            span = tracer.start_span("child_1")
            span.finish()
        
        # Create trace 2
        with tracer.start_span("op2", trace_id="trace_2"):
            span = tracer.start_span("child_2")
            span.finish()
        
        # Query each trace separately
        trace_1 = Query(collector).by_trace_id("trace_1").execute()
        trace_2 = Query(collector).by_trace_id("trace_2").execute()
        
        assert len(trace_1) == 2
        assert len(trace_2) == 2
        assert all(s.trace_id == "trace_1" for s in trace_1)
        assert all(s.trace_id == "trace_2" for s in trace_2)
    
    def test_error_capture_through_lifecycle(self):
        """Verify errors are captured through context manager."""
        collector = MemoryCollector()
        tracer = Tracer(collector=collector)
        
        error_occurred = False
        try:
            with tracer.start_span("risky_operation") as span:
                span.add_event("operation_started")
                raise ValueError("Something went wrong")
        except ValueError:
            error_occurred = True
        
        assert error_occurred
        
        # Verify span captured error
        results = Query(collector).by_name("risky_operation").with_errors().execute()
        
        assert len(results) == 1
        assert results[0].attributes["error"] == "true"
        assert results[0].attributes["error.type"] == "ValueError"
        assert "Something went wrong" in results[0].attributes["error.message"]
        assert len(results[0].events) == 1  # operation_started was captured
    
    def test_span_lifecycle_timing(self):
        """Verify duration calculated correctly through lifecycle."""
        collector = MemoryCollector()
        tracer = Tracer(collector=collector)
        
        span = tracer.start_span("timed_operation")
        start = time.time()
        time.sleep(0.05)  # Sleep 50ms
        span.finish()
        elapsed = (time.time() - start) * 1000  # Convert to ms
        
        results = Query(collector).by_name("timed_operation").execute()
        
        assert len(results) == 1
        recorded_duration = results[0].duration
        # Allow some tolerance
        assert abs(recorded_duration - 50) < 20  # Within 20ms of actual


class TestMetricsCollection:
    """Test metrics collected through lifecycle."""
    
    def test_metrics_track_all_operations(self):
        """Verify metrics accurately track all operations."""
        collector = MemoryCollector()
        tracer = Tracer(collector=collector)
        
        # Create varied spans
        for i in range(3):
            span = tracer.start_span("database_query")
            span.finish()
        
        for i in range(2):
            span = tracer.start_span("api_call")
            span.finish()
        
        span = tracer.start_span("cache_lookup")
        span.finish()
        
        # Check metrics
        assert tracer.span_count() == 6
        counts = tracer.span_counts_by_name()
        assert counts["database_query"] == 3
        assert counts["api_call"] == 2
        assert counts["cache_lookup"] == 1
    
    def test_error_metrics_accurate(self):
        """Verify error metrics calculated correctly."""
        collector = MemoryCollector()
        tracer = Tracer(collector=collector)
        
        # Create successful spans
        for i in range(7):
            span = tracer.start_span(f"op_{i}")
            span.finish()
        
        # Create error spans
        for i in range(3):
            span = tracer.start_span(f"error_op_{i}")
            span.attributes["error"] = "true"
            span.finish()
        
        # Verify metrics
        assert tracer.span_count() == 10
        assert tracer.error_count() == 3
        assert tracer.error_rate() == pytest.approx(0.3, abs=0.01)
    
    def test_duration_stats_across_spans(self):
        """Verify duration stats aggregated across multiple spans."""
        collector = MemoryCollector()
        tracer = Tracer(collector=collector)
        
        # Create spans with different durations
        durations = [0.01, 0.05, 0.02]
        for duration in durations:
            span = tracer.start_span("operation")
            time.sleep(duration)
            span.finish()
        
        stats = tracer.duration_stats()
        
        assert stats["count"] == 3
        assert stats["min"] > 10  # At least 10ms
        assert stats["max"] > 40  # At least 40ms
        assert stats["avg"] > 20  # Average should be around 26ms


class TestQueryIntegration:
    """Test Query API integration with collector."""
    
    def test_query_filter_combination(self):
        """Verify complex query combinations work end-to-end."""
        collector = MemoryCollector()
        tracer = Tracer(collector=collector)
        
        # Create diverse data
        with tracer.start_span("api_request", trace_id="trace_1") as api:
            with tracer.start_span("database_query") as db:
                db.attributes["error"] = "true"
                db.finish()
        
        with tracer.start_span("api_request", trace_id="trace_2") as api:
            with tracer.start_span("cache_lookup") as cache:
                cache.finish()
        
        # Complex query: trace_1 with errors
        results = (Query(collector)
                   .by_trace_id("trace_1")
                   .with_errors()
                   .execute())
        
        assert len(results) == 1
        assert results[0].name == "database_query"
        assert results[0].trace_id == "trace_1"
    
    def test_sorting_pagination_together(self):
        """Verify sorting and pagination work together."""
        collector = MemoryCollector()
        tracer = Tracer(collector=collector)
        
        # Create spans with varying durations
        for i in range(5):
            span = tracer.start_span(f"op_{i}")
            time.sleep(0.01 * (i + 1))  # Increasing duration
            span.finish()
        
        # Get slowest 2
        results = (Query(collector)
                   .sort_by_duration("desc")
                   .limit(2)
                   .execute())
        
        assert len(results) == 2
        # Should be the slowest (op_4 and op_3)
        assert "op_" in results[0].name
        assert results[0].duration >= results[1].duration
