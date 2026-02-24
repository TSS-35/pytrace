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