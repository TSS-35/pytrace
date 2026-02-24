from pytrace.tracer import Tracer
from pytrace.span import Span
from collector.memory import MemoryCollector
from pytrace.config import Config

def test_tracer_starts_span_with_generated_ids():
    """Tracer should create a span and generate a trace_id if none exists."""
    tracer = Tracer()
    span = tracer.start_span("operation_name")
    
    assert isinstance(span, Span)
    assert span.name == "operation_name"
    assert span.trace_id is not None
    assert len(span.trace_id) == 32  # Check hex string length

def test_tracer_respects_provided_ids():
    """Tracer should use provided IDs, useful for distributed tracing."""
    tracer = Tracer()
    custom_trace_id = "manual_trace_123"
    span = tracer.start_span("child_op", trace_id=custom_trace_id)
    
    assert span.trace_id == custom_trace_id

def test_tracer_manages_active_span():
    tracer = Tracer()
    
    # Use context manager (which we need to implement in Span)
    with tracer.start_span("parent") as parent:
        assert tracer.active_span == parent
        
        with tracer.start_span("child") as child:
            assert tracer.active_span == child
            assert child.parent_id == parent.span_id
            assert child.trace_id == parent.trace_id
            
        # After child exits, parent should be active again
        assert tracer.active_span == parent
        
    # After parent exits, nothing should be active
    assert tracer.active_span is None

def test_distributed_trace_linkage():
    """Test that the tracer can resume a trace from external IDs."""
    tracer = Tracer()
    
    # These would normally come from HTTP headers like 'X-Trace-Id'
    external_trace_id = "external-uuid-001"
    external_span_id = "parent-span-001"
    
    # Service B starts a span using Service A's IDs
    span = tracer.start_span(
        "incoming-api-request", 
        trace_id=external_trace_id, 
        parent_id=external_span_id
    )
    
    assert span.trace_id == external_trace_id
    assert span.parent_id == external_span_id
    
    # Ensure nested spans inside Service B still follow the external trace
    with span:
        child_span = tracer.start_span("database-query")
        assert child_span.trace_id == external_trace_id
        assert child_span.parent_id == span.span_id

def test_automatic_function_tracing():
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    def my_function():
        return "hello"

    tracer.start_auto_trace() # New method to implement
    my_function()
    tracer.stop_auto_trace()
    
    assert len(collector.spans) > 0
    assert collector.spans[0].name == "my_function"

def test_auto_trace_captures_nested_calls():
    collector = MemoryCollector()
    # We need a config that doesn't exclude the test itself
    config = Config() 
    tracer = Tracer(config=config, collector=collector)

    def child_func():
        return "child"

    def parent_func():
        child_func()
        return "parent"

    tracer.start_auto_trace()
    parent_func()
    tracer.stop_auto_trace()

    # We expect 2 spans: parent_func and child_func
    assert len(collector.spans) == 2
    
    # Sort by start time to identify parent and child
    spans = sorted(collector.spans, key=lambda x: x.start_time)
    parent_span = spans[0]
    child_span = spans[1]

    assert parent_span.name == "parent_func"
    assert child_span.name == "child_func"
    
    # The Magic: Verify the linkage
    assert child_span.parent_id == parent_span.span_id
    assert child_span.trace_id == parent_span.trace_id

def test_auto_trace_captures_exceptions():
    collector = MemoryCollector()
    tracer = Tracer(config=Config(), collector=collector)

    def faulty_function():
        raise RuntimeError("Auto-trace crash!")

    tracer.start_auto_trace()
    try:
        faulty_function()
    except RuntimeError:
        pass
    tracer.stop_auto_trace()

    # Verify span was captured and has error metadata
    assert len(collector.spans) >= 1
    span = next(s for s in collector.spans if s.name == "faulty_function")
    
    assert span.attributes["error"] == "true"
    assert span.attributes["error.type"] == "RuntimeError"
    assert span.attributes["error.message"] == "Auto-trace crash!"


def test_extract_trace_context():
    """Verify tracer can extract trace context from a span for distributed tracing."""
    tracer = Tracer()
    
    with tracer.start_span("parent", trace_id="trace_123") as span:
        # Extract context that would be sent to another service (e.g., in HTTP headers)
        context = tracer.extract_context(span)
    
    assert context["trace_id"] == "trace_123"
    assert context["span_id"] == span.span_id
    assert context["trace_flags"] == "01"  # Sampled


def test_inject_trace_context():
    """Verify tracer can inject trace context into spans for child services."""
    tracer = Tracer()
    
    # Simulate receiving context from another service
    incoming_context = {
        "trace_id": "external_trace_456",
        "span_id": "external_span_789",
        "trace_flags": "01"
    }
    
    # Create a span using injected context
    span = tracer.inject_context(
        incoming_context,
        name="received_request"
    )
    
    assert span.trace_id == "external_trace_456"
    assert span.parent_id == "external_span_789"


def test_http_header_propagation():
    """Verify trace context can be extracted to HTTP headers."""
    tracer = Tracer()
    
    with tracer.start_span("service_a_call", trace_id="http_trace_001") as span:
        # Extract as HTTP headers format
        headers = tracer.extract_as_http_headers(span)
    
    assert headers["traceparent"] is not None
    # Format should be: version-trace_id-span_id-trace_flags
    parts = headers["traceparent"].split("-")
    assert len(parts) == 4
    assert parts[0] == "00"  # W3C Trace Context version
    assert parts[1] == "http_trace_001"
    assert parts[3] == "01"  # Sampled


def test_http_header_injection():
    """Verify tracer can consume HTTP headers to continue a trace."""
    tracer = Tracer()
    
    # Simulate headers from service A
    headers = {"traceparent": "00-http_trace_002-parent_span_999-01"}
    
    # Service B receives and creates a new span
    span = tracer.from_http_headers(headers, name="service_b_call")
    
    assert span.trace_id == "http_trace_002"
    assert span.parent_id == "parent_span_999"


def test_tracer_span_count():
    """Verify tracer tracks total spans created."""
    tracer = Tracer()
    
    assert tracer.span_count() == 0
    
    span1 = tracer.start_span("op_1")
    assert tracer.span_count() == 1
    
    span2 = tracer.start_span("op_2")
    assert tracer.span_count() == 2
    
    span1.finish()
    span2.finish()
    assert tracer.span_count() == 2


def test_tracer_error_count():
    """Verify tracer tracks spans with errors."""
    tracer = Tracer()
    
    # Create successful span
    span1 = tracer.start_span("op_1")
    span1.finish()
    
    # Create span with error
    span2 = tracer.start_span("op_2")
    span2.attributes["error"] = "true"
    span2.finish()
    
    # Create another error span
    span3 = tracer.start_span("op_3")
    span3.attributes["error"] = "true"
    span3.finish()
    
    assert tracer.error_count() == 2
    assert tracer.error_rate() == 2/3  # 2 errors out of 3 spans


def test_tracer_span_duration_stats():
    """Verify tracer calculates duration statistics."""
    import time
    tracer = Tracer()
    
    # Create spans with different durations
    span1 = tracer.start_span("fast_op")
    time.sleep(0.01)
    span1.finish()
    
    span2 = tracer.start_span("slow_op")
    time.sleep(0.05)
    span2.finish()
    
    span3 = tracer.start_span("medium_op")
    time.sleep(0.02)
    span3.finish()
    
    stats = tracer.duration_stats()
    
    assert "min" in stats
    assert "max" in stats
    assert "avg" in stats
    assert stats["min"] <= stats["avg"] <= stats["max"]
    assert stats["count"] == 3


def test_tracer_span_by_name():
    """Verify tracer can report span counts by operation name."""
    tracer = Tracer()
    
    for i in range(3):
        span = tracer.start_span("database_query")
        span.finish()
    
    for i in range(2):
        span = tracer.start_span("api_call")
        span.finish()
    
    counts = tracer.span_counts_by_name()
    
    assert counts["database_query"] == 3
    assert counts["api_call"] == 2


def test_tracer_metrics_reset():
    """Verify tracer metrics can be reset."""
    tracer = Tracer()
    
    span = tracer.start_span("op_1")
    span.finish()
    
    assert tracer.span_count() == 1
    
    tracer.reset_metrics()
    
    assert tracer.span_count() == 0
    assert tracer.error_count() == 0