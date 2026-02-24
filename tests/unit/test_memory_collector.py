from collector.memory import MemoryCollector, BatchMemoryCollector
from pytrace.span import Span
from pytrace.tracer import Tracer
import time

def test_memory_collector_stores_spans():
    collector = MemoryCollector()
    span = Span(name="test", trace_id="123")
    span.finish()
    
    collector.send_span(span)
    
    assert len(collector.spans) == 1
    assert collector.spans[0].name == "test"

def test_memory_collector_clear():
    collector = MemoryCollector()
    collector.send_span(Span(name="test", trace_id="123"))
    collector.clear()
    assert len(collector.spans) == 0


def test_collector_buffering():
    """Verify collector can buffer spans before processing."""
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    # Create multiple spans
    for i in range(5):
        span = tracer.start_span(f"operation_{i}")
        span.finish()
    
    assert len(collector.spans) == 5
    assert collector.span_count() == 5


def test_collector_flush():
    """Verify collector can flush buffered spans."""
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    # Create and finish some spans
    for i in range(3):
        span = tracer.start_span(f"op_{i}")
        span.finish()
    
    initial_count = len(collector.spans)
    assert initial_count == 3
    
    # Flush should clear the buffer
    flushed_spans = collector.flush()
    
    assert len(flushed_spans) == 3
    assert len(collector.spans) == 0


def test_batch_collector_threshold():
    """Verify batch collector flushes when threshold is reached."""
    collector = BatchMemoryCollector(batch_size=3)
    tracer = Tracer(collector=collector)
    
    # Add spans
    for i in range(2):
        span = tracer.start_span(f"op_{i}")
        span.finish()
    
    # Should not auto-flush yet
    assert len(collector.current_batch) == 2
    assert len(collector.flushed_batches) == 0
    
    # Add one more to trigger flush
    span = tracer.start_span("op_3")
    span.finish()
    
    # Should auto-flush when batch_size reached
    assert len(collector.current_batch) == 0
    assert len(collector.flushed_batches) == 1
    assert len(collector.flushed_batches[0]) == 3


def test_auto_flush_timer():
    """Verify collector can auto-flush after a time interval."""
    collector = BatchMemoryCollector(batch_size=10, flush_interval_ms=50)
    tracer = Tracer(collector=collector)
    
    # Add span
    span = tracer.start_span("timed_op")
    span.finish()
    
    assert len(collector.current_batch) == 1
    
    # Wait for flush interval
    time.sleep(0.1)
    
    # Should auto-flush after interval
    assert len(collector.current_batch) == 0
    assert len(collector.flushed_batches) >= 1