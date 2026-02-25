"""Tests for HTTP API server (TDD - failing tests first)."""
import json
import time
import pytest
from pytrace.tracer import Tracer
from pytrace.server import create_app
from collector.memory import MemoryCollector


@pytest.fixture
def app():
    """Create test Flask app."""
    collector = MemoryCollector()
    app = create_app(collector)
    app.config['TESTING'] = True
    return app, collector


@pytest.fixture
def client(app):
    """Create test client."""
    app_instance, _ = app
    return app_instance.test_client()


@pytest.fixture
def sample_data(app):
    """Create sample trace data."""
    app_instance, collector = app
    tracer = Tracer(collector=collector)
    
    # Trace 1: Successful operations
    with tracer.start_span("api_request", trace_id="trace_001") as api:
        api.add_event("request_received", attributes={"endpoint": "/users"})
        
        with tracer.start_span("database_query") as db:
            db.add_event("executing_query", attributes={"query": "SELECT * FROM users"})
            db.finish()
        
        api.add_event("response_sent", attributes={"status": 200})
    
    # Trace 2: Error operation
    with tracer.start_span("api_request", trace_id="trace_002") as api:
        api.add_event("request_received", attributes={"endpoint": "/posts"})
        
        with tracer.start_span("database_query") as db:
            db.attributes["error"] = "true"
            db.attributes["error.type"] = "ConnectionError"
            db.finish()
        
        api.attributes["error"] = "true"
        api.add_event("error_response", attributes={"status": 500})
    
    # Trace 3: Cache operation
    with tracer.start_span("cache_lookup", trace_id="trace_003") as cache:
        cache.add_event("cache_hit", attributes={"key": "user_123"})
    
    return tracer


def test_health_check(client):
    """Verify health check endpoint."""
    response = client.get('/api/health')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'


def test_get_all_spans(client, sample_data):
    """Verify get all spans endpoint."""
    response = client.get('/api/spans')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'spans' in data
    assert len(data['spans']) == 5  # 3 parent spans + 2 child spans


def test_get_spans_with_query_filters(client, sample_data):
    """Verify spans endpoint with query filters."""
    # Filter by name
    response = client.get('/api/spans?name=database_query')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    spans = data['spans']
    assert len(spans) == 2
    assert all(span['name'] == 'database_query' for span in spans)


def test_get_spans_with_error_filter(client, sample_data):
    """Verify spans endpoint can filter by error."""
    response = client.get('/api/spans?error=true')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    spans = data['spans']
    assert len(spans) == 2  # 1 database_query + 1 api_request
    assert all(span['attributes'].get('error') == 'true' for span in spans)


def test_get_spans_with_trace_id_filter(client, sample_data):
    """Verify spans endpoint can filter by trace_id."""
    response = client.get('/api/spans?trace_id=trace_001')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    spans = data['spans']
    assert len(spans) == 2
    assert all(span['trace_id'] == 'trace_001' for span in spans)


def test_get_span_by_id(client, sample_data):
    """Verify get span by ID endpoint."""
    # First get all spans to get a span_id
    response = client.get('/api/spans')
    spans = json.loads(response.data)['spans']
    span_id = spans[0]['span_id']
    
    # Now get specific span
    response = client.get(f'/api/spans/{span_id}')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'span' in data
    assert data['span']['span_id'] == span_id


def test_get_span_not_found(client):
    """Verify 404 when span not found."""
    response = client.get('/api/spans/nonexistent_span_id')
    
    assert response.status_code == 404


def test_get_trace(client, sample_data):
    """Verify get entire trace endpoint."""
    response = client.get('/api/traces/trace_001')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'trace' in data
    spans = data['trace']
    assert len(spans) == 2
    assert all(span['trace_id'] == 'trace_001' for span in spans)


def test_get_trace_not_found(client):
    """Verify 404 when trace not found."""
    response = client.get('/api/traces/nonexistent_trace')
    
    assert response.status_code == 404


def test_list_traces(client, sample_data):
    """Verify list traces endpoint."""
    response = client.get('/api/traces')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'traces' in data
    traces = data['traces']
    assert len(traces) == 3
    assert all('trace_id' in trace for trace in traces)
    assert all('span_count' in trace for trace in traces)


def test_list_traces_with_error_filter(client, sample_data):
    """Verify list traces can filter by error."""
    response = client.get('/api/traces?error=true')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    traces = data['traces']
    assert len(traces) == 1  # Only trace_002 has errors
    assert traces[0]['trace_id'] == 'trace_002'


def test_get_metrics(client, sample_data):
    """Verify metrics endpoint."""
    response = client.get('/api/metrics')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert 'total_spans' in data
    assert 'error_count' in data
    assert 'error_rate' in data
    assert 'duration_stats' in data
    assert 'operations' in data
    
    assert data['total_spans'] == 5
    assert data['error_count'] == 2
    assert data['error_rate'] == pytest.approx(0.4, abs=0.01)


def test_list_operations(client, sample_data):
    """Verify list operations endpoint."""
    response = client.get('/api/operations')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'operations' in data
    
    operations = {op['name']: op['count'] for op in data['operations']}
    assert operations['api_request'] == 2
    assert operations['database_query'] == 2
    assert operations['cache_lookup'] == 1


def test_query_spans_with_sorting(client, sample_data):
    """Verify spans endpoint supports sorting."""
    # Sort by duration descending
    response = client.get('/api/spans?sort=duration&order=desc')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    spans = data['spans']
    
    # Verify descending order (or all same duration)
    durations = [s['duration'] for s in spans if s['duration'] is not None]
    if len(durations) > 1:
        assert durations == sorted(durations, reverse=True)


def test_query_spans_with_limit(client, sample_data):
    """Verify spans endpoint supports limit."""
    response = client.get('/api/spans?limit=2')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    spans = data['spans']
    assert len(spans) == 2


def test_query_spans_with_offset(client, sample_data):
    """Verify spans endpoint supports offset."""
    # Get all spans
    response = client.get('/api/spans')
    all_spans = json.loads(response.data)['spans']
    
    # Get with offset
    response = client.get('/api/spans?offset=2')
    offset_spans = json.loads(response.data)['spans']
    
    assert len(offset_spans) == len(all_spans) - 2


def test_span_json_serialization(client, sample_data):
    """Verify span JSON contains all required fields."""
    response = client.get('/api/spans')
    spans = json.loads(response.data)['spans']
    span = spans[0]
    
    required_fields = [
        'span_id', 'name', 'trace_id', 'parent_id',
        'start_time', 'end_time', 'duration',
        'attributes', 'events'
    ]
    
    for field in required_fields:
        assert field in span, f"Missing field: {field}"


def test_trace_summary(client, sample_data):
    """Verify trace summary has correct metadata."""
    response = client.get('/api/traces')
    data = json.loads(response.data)
    traces = data['traces']
    
    # Find trace_001
    trace = next(t for t in traces if t['trace_id'] == 'trace_001')
    
    assert 'trace_id' in trace
    assert 'span_count' in trace
    assert 'duration' in trace
    assert 'error_count' in trace
    assert 'status' in trace  # 'success' or 'error'


def test_combined_filters(client, sample_data):
    """Verify combining multiple query parameters."""
    response = client.get('/api/spans?trace_id=trace_001&name=database_query')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    spans = data['spans']
    
    assert len(spans) == 1
    assert spans[0]['trace_id'] == 'trace_001'
    assert spans[0]['name'] == 'database_query'


def test_api_error_response_format(client):
    """Verify error responses have consistent format."""
    response = client.get('/api/spans/nonexistent')
    
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data
    assert 'message' in data


def test_invalid_query_parameter(client):
    """Verify graceful handling of invalid parameters."""
    response = client.get('/api/spans?limit=invalid')
    
    # Should either return 400 or handle gracefully with default
    assert response.status_code in (400, 200)
