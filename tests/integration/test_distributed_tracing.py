"""Integration tests for distributed tracing."""
import pytest
from pytrace.tracer import Tracer
from pytrace.query import Query
from collector.memory import MemoryCollector


class TestDistributedTracing:
    """Test trace context propagation across services."""
    
    def test_extract_and_inject_context(self):
        """Verify context extraction and injection for distributed tracing."""
        # Service A
        collector_a = MemoryCollector()
        tracer_a = Tracer(collector=collector_a)
        
        with tracer_a.start_span("send_request", trace_id="global_trace_1") as span_a:
            # Extract context to send to Service B
            context = tracer_a.extract_context(span_a)
        
        # Service B
        collector_b = MemoryCollector()
        tracer_b = Tracer(collector=collector_b)
        
        # Inject context from Service A
        span_b = tracer_b.inject_context(context, name="receive_request")
        
        # Verify linkage
        assert span_b.trace_id == "global_trace_1"
        assert span_b.parent_id == span_a.span_id
    
    def test_w3c_header_propagation(self):
        """Verify W3C Trace Context header format."""
        collector = MemoryCollector()
        tracer = Tracer(collector=collector)
        
        with tracer.start_span("service_call", trace_id="abc123def456") as span:
            headers = tracer.extract_as_http_headers(span)
        
        # Verify W3C format
        assert "traceparent" in headers
        parts = headers["traceparent"].split("-")
        assert len(parts) == 4
        assert parts[0] == "00"  # version
        assert parts[1] == "abc123def456"  # trace_id
        assert parts[2] == span.span_id  # span_id
        assert parts[3] == "01"  # sampled
    
    def test_w3c_header_round_trip(self):
        """Verify W3C headers can be extracted and re-injected."""
        # Service A creates context and extracts headers
        collector_a = MemoryCollector()
        tracer_a = Tracer(collector=collector_a)
        
        with tracer_a.start_span("client_request", trace_id="xyz789") as span_a:
            headers = tracer_a.extract_as_http_headers(span_a)
        
        # Service B receives headers and creates span
        collector_b = MemoryCollector()
        tracer_b = Tracer(collector=collector_b)
        
        span_b = tracer_b.from_http_headers(headers, name="server_request")
        
        # Verify round-trip
        assert span_b.trace_id == span_a.trace_id
        assert span_b.parent_id == span_a.span_id
    
    def test_multi_hop_distributed_trace(self):
        """Verify trace continues across multiple service hops."""
        trace_id = "distributed_trace_001"
        
        # Service A
        collector_a = MemoryCollector()
        tracer_a = Tracer(collector=collector_a)
        with tracer_a.start_span("service_a", trace_id=trace_id) as span_a:
            headers_ab = tracer_a.extract_as_http_headers(span_a)
        
        # Service B
        collector_b = MemoryCollector()
        tracer_b = Tracer(collector=collector_b)
        span_b = tracer_b.from_http_headers(headers_ab, name="service_b")
        with tracer_b.start_span("internal_op") as inner_b:
            headers_bc = tracer_b.extract_as_http_headers(span_b)
        
        # Service C
        collector_c = MemoryCollector()
        tracer_c = Tracer(collector=collector_c)
        span_c = tracer_c.from_http_headers(headers_bc, name="service_c")
        
        # Verify trace continuity
        assert span_b.trace_id == trace_id
        assert span_c.trace_id == trace_id
        assert span_b.parent_id == span_a.span_id
        # span_c's parent should be span_b
        assert span_c.parent_id == span_b.span_id
    
    def test_child_spans_maintain_parent(self):
        """Verify child spans created after context injection maintain hierarchy."""
        # Service A
        collector_a = MemoryCollector()
        tracer_a = Tracer(collector=collector_a)
        
        with tracer_a.start_span("request", trace_id="trace_x") as span_a:
            context = tracer_a.extract_context(span_a)
        
        # Service B receives and creates children
        collector_b = MemoryCollector()
        tracer_b = Tracer(collector=collector_b)
        
        # span_b is created from injected context - it becomes the parent in Service B
        span_b = tracer_b.inject_context(context, name="received_request")
        with span_b:
            with tracer_b.start_span("child_1") as child_1:
                child_1.finish()
            with tracer_b.start_span("child_2") as child_2:
                child_2.finish()
        
        # Verify hierarchy
        all_spans = Query(collector_b).by_trace_id("trace_x").execute()
        
        # received_request is the root in Service B (but has parent from Service A)
        received_request = [s for s in all_spans if s.name == "received_request"]
        child_spans = [s for s in all_spans if s.parent_id == received_request[0].span_id]
        
        # Should have 1 received_request and 2 children under it
        assert len(received_request) == 1
        assert len(child_spans) == 2
        assert all(child.parent_id == received_request[0].span_id for child in child_spans)


class TestCrossServiceMetrics:
    """Test metrics across multiple collectors (services)."""
    
    def test_distributed_error_tracking(self):
        """Verify errors propagate through distributed trace."""
        # Service A - no error
        collector_a = MemoryCollector()
        tracer_a = Tracer(collector=collector_a)
        
        with tracer_a.start_span("api_call", trace_id="dist_trace") as span_a:
            context = tracer_a.extract_context(span_a)
        
        # Service B - has error
        collector_b = MemoryCollector()
        tracer_b = Tracer(collector=collector_b)
        
        span_b = tracer_b.inject_context(context, name="database_query")
        span_b.attributes["error"] = "true"
        span_b.attributes["error.type"] = "ConnectionError"
        span_b.finish()
        
        # Verify error in Service B but not A
        assert tracer_a.error_count() == 0
        assert tracer_b.error_count() == 1
        
        # Verify error in Query
        errors_b = Query(collector_b).with_errors().execute()
        assert len(errors_b) == 1
        assert errors_b[0].trace_id == "dist_trace"
