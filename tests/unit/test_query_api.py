"""Tests for span query API (TDD - failing tests first)."""
import time
from pytrace.tracer import Tracer
from pytrace.query import Query
from collector.memory import MemoryCollector


def test_query_all_spans():
    """Verify query can retrieve all spans."""
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    # Create multiple spans
    for i in range(3):
        span = tracer.start_span(f"op_{i}")
        span.finish()
    
    query = Query(collector)
    results = query.execute()
    
    assert len(results) == 3


def test_query_filter_by_trace_id():
    """Verify query can filter spans by trace_id."""
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    # Create spans with different trace IDs
    trace_1 = tracer.start_span("op_1", trace_id="trace_001")
    trace_1.finish()
    
    trace_2 = tracer.start_span("op_2", trace_id="trace_002")
    trace_2.finish()
    
    trace_3 = tracer.start_span("op_3", trace_id="trace_001")  # Same as trace_1
    trace_3.finish()
    
    query = Query(collector).by_trace_id("trace_001")
    results = query.execute()
    
    assert len(results) == 2
    assert all(span.trace_id == "trace_001" for span in results)


def test_query_filter_by_span_name():
    """Verify query can filter spans by operation name."""
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    # Create spans with different names
    span1 = tracer.start_span("database_query")
    span1.finish()
    
    span2 = tracer.start_span("api_call")
    span2.finish()
    
    span3 = tracer.start_span("database_query")
    span3.finish()
    
    query = Query(collector).by_name("database_query")
    results = query.execute()
    
    assert len(results) == 2
    assert all(span.name == "database_query" for span in results)


def test_query_filter_by_error():
    """Verify query can filter spans with errors."""
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    # Create successful span
    span1 = tracer.start_span("op_1")
    span1.finish()
    
    # Create error spans
    span2 = tracer.start_span("op_2")
    span2.attributes["error"] = "true"
    span2.finish()
    
    span3 = tracer.start_span("op_3")
    span3.attributes["error"] = "true"
    span3.finish()
    
    query = Query(collector).with_errors()
    results = query.execute()
    
    assert len(results) == 2
    assert all(span.attributes.get("error") == "true" for span in results)


def test_query_filter_by_duration():
    """Verify query can filter spans by duration range."""
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    # Create spans with different durations
    span1 = tracer.start_span("fast")
    time.sleep(0.01)
    span1.finish()
    
    span2 = tracer.start_span("slow")
    time.sleep(0.05)
    span2.finish()
    
    span3 = tracer.start_span("medium")
    time.sleep(0.02)
    span3.finish()
    
    # Query spans between 15ms and 60ms
    query = Query(collector).by_duration_range(15, 60)
    results = query.execute()
    
    assert len(results) == 2
    assert all(15 <= span.duration <= 60 for span in results)


def test_query_combine_filters():
    """Verify query can combine multiple filters."""
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    # Create various spans
    span1 = tracer.start_span("db_query", trace_id="trace_1")
    span1.finish()
    
    span2 = tracer.start_span("db_query", trace_id="trace_1")
    span2.attributes["error"] = "true"
    span2.finish()
    
    span3 = tracer.start_span("api_call", trace_id="trace_2")
    span3.attributes["error"] = "true"
    span3.finish()
    
    # Filter: trace_1 AND db_query AND errors
    query = Query(collector).by_trace_id("trace_1").by_name("db_query").with_errors()
    results = query.execute()
    
    assert len(results) == 1
    assert results[0].trace_id == "trace_1"
    assert results[0].name == "db_query"
    assert results[0].attributes["error"] == "true"


def test_query_sort_by_duration():
    """Verify query can sort results by duration."""
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    # Create spans with different durations
    span1 = tracer.start_span("op_1")
    time.sleep(0.05)
    span1.finish()
    
    span2 = tracer.start_span("op_2")
    time.sleep(0.01)
    span2.finish()
    
    span3 = tracer.start_span("op_3")
    time.sleep(0.03)
    span3.finish()
    
    # Sort ascending
    query = Query(collector).sort_by_duration("asc")
    results = query.execute()
    
    assert results[0].duration <= results[1].duration <= results[2].duration


def test_query_sort_by_start_time():
    """Verify query can sort results by start_time."""
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    # Create spans with time gaps
    span1 = tracer.start_span("op_1")
    span1.finish()
    time.sleep(0.01)
    
    span2 = tracer.start_span("op_2")
    span2.finish()
    time.sleep(0.01)
    
    span3 = tracer.start_span("op_3")
    span3.finish()
    
    # Sort descending (newest first)
    query = Query(collector).sort_by_start_time("desc")
    results = query.execute()
    
    assert results[0].start_time >= results[1].start_time >= results[2].start_time


def test_query_limit():
    """Verify query can limit results."""
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    # Create 5 spans
    for i in range(5):
        span = tracer.start_span(f"op_{i}")
        span.finish()
    
    query = Query(collector).limit(3)
    results = query.execute()
    
    assert len(results) == 3


def test_query_offset():
    """Verify query can skip results with offset."""
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    # Create spans with names for easy identification
    for i in range(5):
        span = tracer.start_span(f"op_{i}")
        span.finish()
    
    # Get all spans sorted by name
    query = Query(collector).sort_by_name("asc")
    all_results = query.execute()
    
    # Get with offset
    query = Query(collector).sort_by_name("asc").offset(2)
    results = query.execute()
    
    assert len(results) == 3
    assert results[0].name == all_results[2].name


def test_query_get_trace():
    """Verify query can get entire trace with all spans."""
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    # Create a trace with parent-child hierarchy
    with tracer.start_span("parent_op", trace_id="trace_1") as parent:
        with tracer.start_span("child_op_1") as child1:
            child1.finish()
        
        with tracer.start_span("child_op_2") as child2:
            child2.finish()
    
    # Get entire trace
    query = Query(collector).by_trace_id("trace_1")
    trace_spans = query.execute()
    
    assert len(trace_spans) == 3
    span_names = {span.name for span in trace_spans}
    assert span_names == {"parent_op", "child_op_1", "child_op_2"}
    assert all(span.trace_id == "trace_1" for span in trace_spans)


def test_query_chaining():
    """Verify query supports method chaining."""
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    # Create test data
    for i in range(10):
        span = tracer.start_span("database_query" if i % 2 == 0 else "api_call")
        if i > 5:
            span.attributes["error"] = "true"
        span.finish()
    
    # Chain multiple operations
    results = (Query(collector)
               .by_name("database_query")
               .with_errors()
               .limit(2)
               .execute())
    
    assert len(results) == 2
    assert all(span.name == "database_query" for span in results)
    assert all(span.attributes.get("error") == "true" for span in results)


def test_query_without_matches():
    """Verify query returns empty list when no matches found."""
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    span = tracer.start_span("operation")
    span.finish()
    
    query = Query(collector).by_trace_id("non_existent_trace")
    results = query.execute()
    
    assert results == []
    assert len(results) == 0


def test_query_count():
    """Verify query can return count without returning spans."""
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    # Create 5 error spans
    for i in range(5):
        span = tracer.start_span(f"op_{i}")
        span.attributes["error"] = "true"
        span.finish()
    
    # Create 3 successful spans
    for i in range(3):
        span = tracer.start_span(f"ok_{i}")
        span.finish()
    
    query = Query(collector).with_errors()
    count = query.count()
    
    assert count == 5
