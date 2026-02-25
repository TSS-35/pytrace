"""Example: Running the pytrace HTTP API server."""

from pytrace.server import create_app
from pytrace.tracer import Tracer
from collector.memory import MemoryCollector
import time
import threading


def run_server_example():
    """Start HTTP API server with sample data."""
    
    # Create collector and populate with sample data
    collector = MemoryCollector()
    tracer = Tracer(collector=collector)
    
    print("Generating sample trace data...")
    
    # Simulate some application traces
    for request_id in range(5):
        with tracer.start_span("api_request", trace_id=f"trace_{request_id:03d}") as api:
            api.add_event("request_received", attributes={
                "endpoint": f"/users/{request_id}",
                "method": "GET"
            })
            
            # Database query
            with tracer.start_span("database_query") as db:
                db.add_event("executing_query", attributes={
                    "table": "users",
                    "operation": "SELECT"
                })
                time.sleep(0.01)  # Simulate work
                
                # Add error for some requests
                if request_id % 3 == 0:
                    db.attributes["error"] = "true"
                    db.attributes["error.type"] = "QueryTimeout"
                
                db.finish()
            
            # Cache lookup
            with tracer.start_span("cache_lookup") as cache:
                cache.add_event("cache_check", attributes={"key": f"user_{request_id}"})
                time.sleep(0.005)
                cache.finish()
            
            api.add_event("response_sent", attributes={
                "status": 500 if (request_id % 3 == 0) else 200
            })
    
    print(f"Generated {len(collector.spans)} spans across 5 traces\n")
    
    # Create Flask app
    app = create_app(collector)
    
    print("=" * 70)
    print("pytrace HTTP API Server")
    print("=" * 70)
    print("\nStarting server on http://localhost:5000")
    print("\nAvailable endpoints:\n")
    
    endpoints = [
        ("GET", "/api/health", "Health check"),
        ("GET", "/api/spans", "List all spans with filters"),
        ("GET", "/api/spans/{span_id}", "Get specific span"),
        ("GET", "/api/traces", "List all traces"),
        ("GET", "/api/traces/{trace_id}", "Get entire trace"),
        ("GET", "/api/operations", "List all operations"),
        ("GET", "/api/metrics", "Get overall metrics"),
    ]
    
    for method, path, description in endpoints:
        print(f"  {method:6} {path:30} - {description}")
    
    print("\nExample queries:")
    print("  - http://localhost:5000/api/spans?name=database_query")
    print("  - http://localhost:5000/api/spans?error=true")
    print("  - http://localhost:5000/api/traces/trace_000")
    print("  - http://localhost:5000/api/metrics")
    print("\nPress CTRL+C to stop the server\n")
    
    # Run the app
    app.run(debug=False, port=5000, use_reloader=False)


if __name__ == "__main__":
    try:
        run_server_example()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
