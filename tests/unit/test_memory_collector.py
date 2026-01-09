from collector.memory import MemoryCollector
from pytrace.span import Span

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