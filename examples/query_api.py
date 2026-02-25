"""Example usage of the Query API."""

from pytrace.tracer import Tracer
from pytrace.query import Query
from collector.memory import MemoryCollector


def example_query_api():
    """Demonstrates the Query API for filtering and analyzing spans."""
    
    # Set up tracing
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    # Simulate some application work
    print("Creating sample traces...")
    
    # Trace 1: Successful database operations
    with tracer.start_span("api_request", trace_id="trace_001") as api:
        api.add_event("request_received", attributes={"endpoint": "/users"})
        
        with tracer.start_span("database_query") as db:
            db.add_event("executing_query", attributes={"query": "SELECT * FROM users"})
            db.finish()
        
        api.add_event("response_sent", attributes={"status": 200})
    
    # Trace 2: Database error
    with tracer.start_span("api_request", trace_id="trace_002") as api:
        api.add_event("request_received", attributes={"endpoint": "/posts"})
        
        with tracer.start_span("database_query") as db:
            try:
                db.attributes["error"] = "true"
                db.attributes["error.type"] = "ConnectionError"
                db.finish()
            except:
                pass
        
        api.attributes["error"] = "true"
        api.add_event("error_response", attributes={"status": 500})
    
    # Trace 3: Cache hit
    with tracer.start_span("cache_lookup", trace_id="trace_003") as cache:
        cache.add_event("cache_hit", attributes={"key": "user_123"})
    
    print(f"\nCollected {len(collector.spans)} total spans\n")
    
    # Query examples
    print("=" * 60)
    print("QUERY EXAMPLES")
    print("=" * 60)
    
    # 1. Get all spans
    print("\n1. All spans:")
    all_spans = Query(collector).execute()
    print(f"   Found {len(all_spans)} spans")
    
    # 2. Get all database queries
    print("\n2. All database queries:")
    db_spans = Query(collector).by_name("database_query").execute()
    for span in db_spans:
        print(f"   - {span.name} (trace: {span.trace_id})")
    
    # 3. Find error spans
    print("\n3. Spans with errors:")
    error_spans = Query(collector).with_errors().execute()
    for span in error_spans:
        error_type = span.attributes.get("error.type", "Unknown")
        print(f"   - {span.name}: {error_type}")
    
    # 4. Get spans from specific trace
    print("\n4. All spans from trace_001:")
    trace_spans = Query(collector).by_trace_id("trace_001").execute()
    for span in trace_spans:
        print(f"   - {span.name} ({span.duration:.2f}ms)")
    
    # 5. Combined filters
    print("\n5. API requests that had errors:")
    api_errors = (Query(collector)
                  .by_name("api_request")
                  .with_errors()
                  .execute())
    for span in api_errors:
        print(f"   - {span.name} from trace {span.trace_id}")
    
    # 6. Slowest operations
    print("\n6. Slowest 2 operations:")
    slowest = Query(collector).sort_by_duration("desc").limit(2).execute()
    for i, span in enumerate(slowest, 1):
        print(f"   {i}. {span.name}: {span.duration:.2f}ms")
    
    # 7. Count errors by operation
    print("\n7. Error counts:")
    db_errors = Query(collector).by_name("database_query").with_errors().count()
    api_errors = Query(collector).by_name("api_request").with_errors().count()
    print(f"   - database_query errors: {db_errors}")
    print(f"   - api_request errors: {api_errors}")
    
    # 8. Pagination
    print("\n8. Pagination (first 2 spans, skip 1):")
    page = Query(collector).offset(1).limit(2).sort_by_start_time("asc").execute()
    for i, span in enumerate(page, 1):
        print(f"   {i}. {span.name}")


if __name__ == "__main__":
    example_query_api()
