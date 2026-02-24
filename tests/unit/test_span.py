import time
from pytrace.span import Span

def test_span_initialization():
    """Verify a span starts with correct metadata and no end_time."""
    span = Span(name="test_op", trace_id="trace_1")
    
    assert span.name == "test_op"
    assert span.trace_id == "trace_1"
    assert span.end_time is None
    assert span.duration is None
    assert isinstance(span.span_id, str)

def test_span_duration_calculation():
    """Verify duration is calculated only after finish() is called."""
    span = Span(name="timed_op", trace_id="trace_1")
    
    # Simulate work
    time.sleep(0.01)
    span.finish()
    
    assert span.end_time is not None
    # Duration should be roughly 10ms
    assert span.duration >= 10
    assert isinstance(span.duration, float)

def test_span_attributes():
    """Verify attributes are stored correctly."""
    span = Span(
        name="attr_test", 
        trace_id="t1", 
        attributes={"db.system": "postgresql"}
    )
    assert span.attributes["db.system"] == "postgresql"

def test_span_context_manager():
    """Tests the 'with' statement functionality."""
    with Span(name="context_test", trace_id="t1") as span:
        assert span.end_time is None
        time.sleep(0.02)
    
    # After exiting the 'with' block, span should be finished
    assert span.end_time is not None
    assert span.duration >= 20

def test_span_manual_finish():
    span = Span(name="manual", trace_id="t1")
    time.sleep(0.01)
    span.finish()
    
    assert span.end_time is not None
    assert span.duration > 0

def test_span_finishes_on_exception():
    """Verify that a span still finishes even if an error occurs."""
    span = Span(name="faulty-op", trace_id="t1")
    
    try:
        with span:
            raise ValueError("Something went wrong!")
    except ValueError:
        pass
    
    assert span.end_time is not None
    assert span.duration > 0

def test_span_captures_error_metadata():
    """Verify that a span records exception details in its attributes."""
    span = Span(name="metadata-test", trace_id="t1")
    
    error_msg = "Database connection failed"
    try:
        with span:
            raise ConnectionError(error_msg)
    except ConnectionError:
        pass
    
    # These will fail until we refactor __exit__
    assert span.attributes["error"] == "true"
    assert span.attributes["error.type"] == "ConnectionError"


def test_span_add_event():
    """Verify that spans can record timestamped events."""
    span = Span(name="test_op", trace_id="trace_1")
    
    # Add an event to the span
    span.add_event("cache_hit", attributes={"cache.key": "user_123"})
    
    assert len(span.events) == 1
    assert span.events[0]["name"] == "cache_hit"
    assert span.events[0]["attributes"]["cache.key"] == "user_123"
    assert "timestamp" in span.events[0]


def test_span_multiple_events():
    """Verify that spans can record multiple events in order."""
    span = Span(name="multi_event_op", trace_id="trace_1")
    
    span.add_event("event_1", attributes={"step": "1"})
    time.sleep(0.01)
    span.add_event("event_2", attributes={"step": "2"})
    time.sleep(0.01)
    span.add_event("event_3", attributes={"step": "3"})
    
    assert len(span.events) == 3
    assert span.events[0]["name"] == "event_1"
    assert span.events[1]["name"] == "event_2"
    assert span.events[2]["name"] == "event_3"
    
    # Verify events are in chronological order
    assert span.events[0]["timestamp"] <= span.events[1]["timestamp"]
    assert span.events[1]["timestamp"] <= span.events[2]["timestamp"]


def test_span_events_in_context():
    """Verify events work within context manager usage."""
    with Span(name="context_event_test", trace_id="t1") as span:
        span.add_event("started", attributes={"status": "initializing"})
        time.sleep(0.01)
        span.add_event("finished", attributes={"status": "complete"})
    
    assert len(span.events) == 2
    assert span.events[0]["name"] == "started"
    assert span.events[1]["name"] == "finished"
