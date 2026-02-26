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
Controls what gets traced and sampling behavior:

```python
from pytrace.config import Config
from pytrace.sampler import ProbabilitySampler

# Basic configuration
config = Config()
tracer = Tracer(config=config)
```

##### Sampling Strategies

pytrace includes multiple sampling strategies to reduce data volume in production without losing critical traces:

```python
from pytrace.sampler import (
    ProbabilitySampler,      # Sample X% of spans
    RateLimitSampler,        # Cap spans per second
    TraceIdSampler,          # Sample entire traces
    AlwaysSampler            # Debug mode (sample all)
)

# 10% probability sampling (production)
config = Config(sampler=ProbabilitySampler(0.1))

# Rate limiting: max 100 spans/second
config = Config(sampler=RateLimitSampler(100))

# Deterministic trace-level sampling (50% of traces)
# Same trace ID always gets same decision - keeps traces complete
config = Config(sampler=TraceIdSampler(0.5))

# Debug mode: capture everything
config = Config(sampler=AlwaysSampler())

tracer = Tracer(config=config, collector=collector)
```

**Sampling Strategy Guide:**

| Strategy | Use Case | Behavior |
|----------|----------|----------|
| `AlwaysSampler` | Development, debugging | Samples every span |
| `ProbabilitySampler(0.01)` | High-volume production | Reduces storage by ~99%, stateless |
| `RateLimitSampler(100)` | Database protection | Caps at fixed rate, token bucket |
| `TraceIdSampler(0.5)` | Distributed systems | Keeps complete traces, 50% sampled |

**Sampler Implementation Notes:**

- **RateLimitSampler**: Thread-safe with internal locking. Safe for concurrent use in multi-threaded applications (Flask, FastAPI, etc.)
- **TraceIdSampler**: Uses stable SHA256 hashing (not Python's built-in hash) to ensure the same trace_id produces consistent sampling decisions across all services in a distributed system

##### Span Redaction (PII Masking)

pytrace can automatically redact sensitive data (passwords, API keys, PII) from span attributes and events:

```python
from pytrace.redactor import Redactor

# Define patterns for sensitive data
patterns = [
    "password",
    "api_key",
    "api_secret",
    "token",
    "ssn",
    "credit_card"
]

redactor = Redactor(patterns=patterns)
config = Config(redactor=redactor)
tracer = Tracer(config=config, collector=collector)

# Sensitive data automatically redacted on span finish
with tracer.start_span("user_login") as span:
    span.attributes["username"] = "alice"          # Preserved
    span.attributes["password"] = "secret123"      # Redacted → ***REDACTED***
    span.add_event("auth_attempt", attributes={
        "token": "jwt_token_xyz",                  # Redacted
        "status": "success"                        # Preserved
    })
```

**Redaction Features:**
- Pattern-based matching (substring and regex)
- Case-insensitive by default
- Custom redaction replacement values
- Recursive redaction of nested attributes
- Redacts both span attributes and event attributes
- Works with any collector backend

**Common Sensitive Patterns:**
```python
# PII (Personally Identifiable Information)
patterns = ["ssn", "social_security_number", "passport", "license"]

# Authentication
patterns = ["password", "pwd", "pin", "token", "secret"]

# Financial
patterns = ["credit_card", "card_number", "cvv", "bank_account"]

# API Security
patterns = ["api_key", "api_secret", "bearer_token", "auth_header"]

# Custom Organization
patterns = ["internal_id", "proprietary_data", "business_secret"]
```

**Custom Redaction Values:**
```python
# Default: ***REDACTED***
redactor = Redactor(patterns=["password"])

# Custom value
redactor = Redactor(patterns=["password"], redaction_value="[MASKED]")

# In compliance logs
redactor = Redactor(patterns=["ssn"], redaction_value="XXX-XX-XXXX")
```

**Advanced Configuration:**

*Safe Mode (Default - Recommended)*
```python
# By default, patterns are treated as literal substrings (safe)
# No ReDoS (Regular Expression Denial of Service) vulnerability
redactor = Redactor(patterns=["password", "token"])  # Safe, literal matching
tracer = Tracer(config=Config(redactor=redactor))
```

*Performance Optimization for High-Volume Tracing*
```python
# Use inplace=True to mutate dictionaries instead of creating copies (~2-3x faster)
# Trade-off: modifies the input dictionary
redactor = Redactor(patterns=["password"], inplace=True)  # For production use
tracer = Tracer(config=Config(redactor=redactor))
```

*Regex Patterns (Advanced)*
```python
# Enable regex if you need complex patterns (requires trusted input only)
# WARNING: Regex patterns can be vulnerable to ReDoS attacks if untrusted
redactor = Redactor(patterns=[r"card_\d{4}"], enable_regex=True)  # Matches "card_1234"

# Safe: Still use enable_regex for trusted patterns
# Avoid patterns like: (a+)+b  or  (a|a)*b  (catastrophic backtracking)
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

The pytrace project follows Test-Driven Development (TDD) practices with comprehensive test coverage across unit and integration tests.

### Running Tests

```bash
# Run all tests (unit + integration)
poetry run pytest tests/ -v

# Run unit tests only
poetry run pytest tests/unit/ -v

# Run integration tests only
poetry run pytest tests/integration/ -v

# Run specific test file
poetry run pytest tests/unit/test_span.py -v

# Run with coverage report
poetry run pytest tests/ --cov=pytrace --cov=collector --cov-report=html
```

## Project Structure

```
pytrace/
├── pytrace/
│   ├── span.py         # Span class with events and context manager
│   ├── tracer.py       # Tracer with auto-instrumentation and metrics
│   ├── config.py       # Module filtering, sampling, and redaction configuration
│   ├── sampler.py      # Sampling strategies (probability, rate-limit, trace-level)
│   ├── redactor.py     # Span redaction for masking sensitive data (PII)
│   ├── query.py        # Query API for filtering and analyzing spans
│   ├── server.py       # Flask HTTP API server
│   └── context.py      # Context variable for active spans
├── collector/
│   ├── base.py         # Abstract collector and MultiCollector
│   ├── memory.py       # Memory and BatchMemoryCollector
│   ├── jsonfile.py     # JSON file persistence
│   └── sqlite.py       # SQLite persistence
├── tests/
│   ├── unit/           # Comprehensive unit tests (119 tests)
│   └── integration/    # Integration tests (60 tests)
├── examples/
│   ├── sampling.py     # Sampling strategy examples
│   ├── redaction.py    # Span redaction examples
│   ├── query_api.py    # Query API examples
│   └── server.py       # HTTP server examples
├── dashboard/          # React web dashboard for trace visualization
│   ├── src/
│   │   ├── components/ # React components (Dashboard, TraceExplorer, etc.)
│   │   ├── api/        # API client
│   │   ├── types/      # TypeScript definitions
│   │   └── App.tsx     # Main app component
│   ├── tests/          # Component unit tests
│   ├── package.json    # npm dependencies
│   └── README.md       # Dashboard documentation
├── pyproject.toml      # Poetry configuration
└── README.md           # This file
```

## HTTP API Server

pytrace includes a built-in Flask API server for querying and analyzing traces over HTTP.

### Starting the Server

```python
from pytrace.server import create_app
from collector.memory import MemoryCollector

collector = MemoryCollector()
app = create_app(collector)
app.run(port=5000)
```

Or run the example:

```bash
poetry run python examples/server.py
```

### API Endpoints

#### **Health Check**
```
GET /api/health
```
Returns server status.

#### **List Spans**
```
GET /api/spans?name=&trace_id=&error=true&sort=&order=&limit=&offset=
```
Query spans with optional filters:
- `name` - Filter by operation name
- `trace_id` - Filter by trace ID
- `error` - Filter to error spans (true/false)
- `sort` - Sort by: duration, start_time, name
- `order` - Sort order: asc, desc
- `limit` - Maximum results
- `offset` - Skip N results

Example:
```bash
curl "http://localhost:5000/api/spans?name=database_query&error=true&sort=duration&order=desc"
```

#### **Get Span**
```
GET /api/spans/{span_id}
```
Get specific span by ID.

#### **List Traces**
```
GET /api/traces?error=true
```
List all traces with optional error filter.

#### **Get Trace**
```
GET /api/traces/{trace_id}
```
Get all spans from a specific trace.

#### **List Operations**
```
GET /api/operations
```
Get operation names and counts.

#### **Get Metrics**
```
GET /api/metrics
```
Get overall metrics including:
- Total span count
- Error count and rate
- Duration statistics (min/max/avg)
- Operation counts

Example response:
```json
{
  "total_spans": 42,
  "error_count": 3,
  "error_rate": 0.071,
  "duration_stats": {
    "min_ms": 0.5,
    "max_ms": 145.2,
    "avg_ms": 23.1,
    "count": 42
  },
  "operations": {
    "database_query": 15,
    "api_call": 12,
    "cache_lookup": 15
  }
}
```

### Common Query Examples

```bash
# Get all database queries
curl "http://localhost:5000/api/spans?name=database_query"

# Get spans with errors
curl "http://localhost:5000/api/spans?error=true"

# Get slowest 10 spans
curl "http://localhost:5000/api/spans?sort=duration&order=desc&limit=10"

# Get entire trace by trace ID
curl "http://localhost:5000/api/traces/trace_001"

# Get metrics for a specific operation
curl "http://localhost:5000/api/spans?name=api_request" | jq '.spans | length'
```

## Web Dashboard

pytrace includes a modern React-based web dashboard for visualizing and analyzing traces in real-time.

### Quick Start

```bash
# Install dependencies
cd dashboard
npm install

# Start development server
npm run dev
```

The dashboard will be available at `http://localhost:5173`

### Features

- **Trace Explorer**: Browse and search distributed traces with detailed span information
- **Operations Dashboard**: Monitor service operations and request counts
- **Latency Analysis**: Visualize trace latencies and performance metrics with charts
- **Error Analysis**: Track and analyze errors across services
- **Responsive Layout**: Optimized for desktop and tablet viewing

### Building for Production

```bash
cd dashboard
npm run build
```

See [dashboard/README.md](dashboard/README.md) for detailed setup, testing, and development instructions.

## Design Principles

1. **Minimal Overhead**: No tracing if not explicitly enabled
2. **Thread-Safe**: Uses context variables for isolation
3. **Flexible**: Multiple collector backends, configurable filtering
4. **Standard**: W3C Trace Context for interoperability
5. **Observable**: Rich metrics and aggregation APIs
6. **Testable**: Comprehensive test coverage with TDD approach