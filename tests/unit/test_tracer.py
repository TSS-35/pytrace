from pytrace.tracer import Tracer
from pytrace.span import Span

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
