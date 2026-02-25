# pytrace

A lightweight distributed tracing framework for Python that captures execution traces, tracks spans across service boundaries, and collects detailed telemetry data.

## Overview

pytrace enables you to:
- **Trace execution** across your Python application with minimal overhead
- **Track latency** with precise timing and duration calculations
- **Propagate context** across distributed services using W3C Trace Context standards
- **Capture events** and attributes for rich operational insights
- **Aggregate metrics** including error rates, latency statistics, and operation counts
- **Query spans** with powerful filtering, sorting, and pagination
- **Persist data** using multiple backends (memory, JSON files, SQLite)

## Installation

```bash
poetry install
```

## Quick Start

### Basic Usage: Manual Tracing

```python
from pytrace.tracer import Tracer
from collector.memory import MemoryCollector

# Initialize tracer with a collector
collector = MemoryCollector()
tracer = Tracer(collector=collector)

# Create and manage spans
with tracer.start_span("database_query") as span:
    span.add_event("query_started", attributes={"query": "SELECT * FROM users"})
    # ... do work ...
    span.add_event("query_complete", attributes={"rows_returned": 42})

# Access collected spans
print(f"Collected {len(collector.spans)} spans")
```

### Automatic Function Tracing

```python
from pytrace.tracer import Tracer
from pytrace.config import Config

config = Config(trace_modules=["myapp"])  # Only trace specific modules
tracer = Tracer(config=config, collector=collector)

def expensive_operation():
    return "result"

# Automatically trace all function calls
tracer.start_auto_trace()
expensive_operation()
tracer.stop_auto_trace()

# Spans are automatically created for each function call
```

### Distributed Tracing

```python
# Service A: Extract trace context for propagation
with tracer.start_span("api_request", trace_id="trace_001") as span:
    headers = tracer.extract_as_http_headers(span)
    # Send headers with HTTP request to Service B
    make_http_request("service-b", headers=headers)

# Service B: Resume trace from incoming headers
headers = incoming_request.headers
span = tracer.from_http_headers(headers, name="process_request")
# Service B's spans are now linked to Service A's trace
```

## Architecture

### Core Components

#### **Span**
Represents a single operation or code block with:
- Start/end timestamps (auto-calculated duration in ms)
- Attributes for metadata (database system, HTTP method, etc.)
- Events for timestamped milestones
- Parent span reference for hierarchy
- Error metadata when exceptions occur

```python
span = tracer.start_span("operation")
span.attributes["db.system"] = "postgresql"
span.add_event("cache_hit", attributes={"cache.key": "user_123"})
span.finish()  # or use context manager
```

#### **Tracer**
Manages span lifecycle and context:
- Creates spans with automatic parent-child linkage
- Maintains active span via context variables (thread-safe)
- Tracks all created spans for metrics
- Supports automatic instrumentation via `sys.settrace()`
- Provides W3C Trace Context extraction/injection

```python
tracer = Tracer(config=config, collector=collector)
span = tracer.start_span("operation_name")

# Access active span in context
current_span = tracer.active_span

# Get metrics
print(tracer.span_count())          # Total spans
print(tracer.error_count())         # Spans with errors
print(tracer.error_rate())          # Error rate (0.0-1.0)
print(tracer.duration_stats())      # Min/max/avg/count
print(tracer.span_counts_by_name()) # Aggregated by operation
```

#### **Collectors**
Persist or buffer spans:

- **MemoryCollector**: In-memory storage with buffering and flush capabilities
- **BatchMemoryCollector**: Batches spans with threshold-based and timer-based auto-flush
- **JsonFileCollector**: Writes spans to JSON files
- **SqliteCollector**: Stores spans in SQLite database
- **MultiCollector**: Routes spans to multiple collectors

```python
from collector.memory import BatchMemoryCollector

# Auto-flush when 100 spans accumulated or 5 seconds elapsed
collector = BatchMemoryCollector(batch_size=100, flush_interval_ms=5000)
tracer = Tracer(collector=collector)

# Manual flush
flushed_spans = collector.flush()
```

#### **Config**
Controls what gets traced:

```python
from pytrace.config import Config

config = Config(
    trace_modules=["myapp.core", "myapp.handlers"],  # Only these
    exclude_modules=["myapp.vendor"]                  # Except these
)
tracer = Tracer(config=config)
```

#### **Query API**
Powerful fluent interface for filtering and analyzing spans:

```python
from pytrace.query import Query

# Basic filtering
Query(collector).by_name("database_query").execute()
Query(collector).by_trace_id("trace_123").execute()
Query(collector).with_errors().execute()

# Sorting
Query(collector).sort_by_duration("desc").execute()       # Slowest first
Query(collector).sort_by_start_time("asc").execute()      # Oldest first

# Duration filtering
Query(collector).by_duration_range(10, 100).execute()     # 10-100ms

# Pagination
Query(collector).limit(10).offset(20).execute()           # Get 10, skip 20

# Chaining
results = (Query(collector)
           .by_name("api_call")
           .with_errors()
           .sort_by_duration("desc")
           .limit(5)
           .execute())

# Counting
error_count = Query(collector).with_errors().count()
```

### Context Variables

pytrace uses Python's `contextvars` for thread-safe active span tracking. Each thread maintains its own active span, enabling safe concurrent tracing:

```python
# In main thread
with tracer.start_span("main") as span1:
    # span1 is active in main thread
    
    # In worker thread
    def worker():
        with tracer.start_span("task") as span2:
            # span2 is active in worker thread
            # span1 and span2 don't interfere
    
    thread = threading.Thread(target=worker)
    thread.start()
```

## Data Flow

```
┌─────────────┐
│   Spans     │
│  (created)  │
└──────┬──────┘
       │
       ├──► active_span_var (context)
       │
       ├──► _spans list (tracer metrics)
       │
       └──► on_finish callback
            └──► collector.send_span()
                 ├──► MemoryCollector (buffer)
                 ├──► JsonFileCollector (persist)
                 ├──► SqliteCollector (persist)
                 └──► MultiCollector (dispatch all)
```

## W3C Trace Context Support

pytrace implements W3C Trace Context for standard cross-service tracing:

```python
# Extract as W3C format
with tracer.start_span("request", trace_id="abc123") as span:
    headers = tracer.extract_as_http_headers(span)
    # headers = {"traceparent": "00-abc123-def456-01"}

# Parse from W3C format
incoming_headers = {"traceparent": "00-abc123-def456-01"}
span = tracer.from_http_headers(incoming_headers, name="response")
```

Format: `version-trace_id-span_id-trace_flags`
- `version`: Protocol version (00)
- `trace_id`: 32-char hex string
- `span_id`: 16-char hex string
- `trace_flags`: Sampling decision (01=sampled, 00=not sampled)

## Metrics & Observability

```python
# Span counting
tracer.span_count()           # Total spans created
tracer.error_count()          # Spans with errors
tracer.error_rate()           # Fraction with errors

# Duration statistics (in milliseconds)
stats = tracer.duration_stats()
# {
#   "count": 10,
#   "min": 5.2,
#   "max": 145.8,
#   "avg": 42.1
# }

# Operation-level aggregation
counts = tracer.span_counts_by_name()
# {"database_query": 5, "api_call": 3, "cache_lookup": 2}

# Reset metrics
tracer.reset_metrics()
```

## Testing

```bash
# Run all tests
poetry run pytest tests/unit/ -v

# Run specific test file
poetry run pytest tests/unit/test_span.py -v

# Run with coverage
poetry run pytest tests/unit/ --cov=pytrace --cov=collector
```

The test suite includes tests covering:
- Span creation, duration, events, and error capture
- Tracer span management and metrics
- Trace context extraction and W3C header propagation
- Collector buffering, flushing, and batching
- Configuration filtering

## Project Structure

```
pytrace/
├── pytrace/
│   ├── span.py         # Span class with events and context manager
│   ├── tracer.py       # Tracer with auto-instrumentation and metrics
│   ├── config.py       # Module filtering configuration
│   └── context.py      # Context variable for active spans
├── collector/
│   ├── base.py         # Abstract collector and MultiCollector
│   ├── memory.py       # Memory and BatchMemoryCollector
│   ├── jsonfile.py     # JSON file persistence
│   └── sqlite.py       # SQLite persistence
├── tests/
│   └── unit/           # Comprehensive unit tests
├── pyproject.toml      # Poetry configuration
└── README.md           # This file
```

## Design Principles

1. **Minimal Overhead**: No tracing if not explicitly enabled
2. **Thread-Safe**: Uses context variables for isolation
3. **Flexible**: Multiple collector backends, configurable filtering
4. **Standard**: W3C Trace Context for interoperability
5. **Observable**: Rich metrics and aggregation APIs
6. **Testable**: Comprehensive test coverage with TDD approach