"""Integration tests for server and collector integration."""
import pytest
import json
from pytrace.tracer import Tracer
from pytrace.server import create_app
from pytrace.query import Query
from collector.memory import MemoryCollector, BatchMemoryCollector


class TestServerCollectorIntegration:
    """Test HTTP server integration with collectors."""
    
    @pytest.fixture
    def server_with_data(self):
        """Create server with sample data."""
        collector = MemoryCollector()
        tracer = Tracer(collector=collector)
        
        # Create sample traces
        with tracer.start_span("api_call", trace_id="trace_001") as api:
            with tracer.start_span("database_query") as db:
                db.attributes["error"] = "true"
                db.finish()
        
        with tracer.start_span("cache_lookup", trace_id="trace_002") as cache:
            cache.finish()
        
        app = create_app(collector)
        app.config['TESTING'] = True
        client = app.test_client()
        
        return client, collector, tracer
    
    def test_server_queries_match_direct_queries(self, server_with_data):
        """Verify server returns same results as direct Query API."""
        client, collector, tracer = server_with_data
        
        # Get errors via direct query
        direct_errors = Query(collector).with_errors().execute()
        
        # Get errors via server
        response = client.get('/api/spans?error=true')
        server_errors = json.loads(response.data)['spans']
        
        assert len(direct_errors) == len(server_errors)
    
    def test_server_metrics_match_tracer(self, server_with_data):
        """Verify server metrics match tracer metrics."""
        client, collector, tracer = server_with_data
        
        # Get metrics via server
        response = client.get('/api/metrics')
        server_metrics = json.loads(response.data)
        
        # Get metrics directly
        assert server_metrics['total_spans'] == tracer.span_count()
        assert server_metrics['error_count'] == tracer.error_count()
    
    def test_server_trace_grouping(self, server_with_data):
        """Verify server correctly groups spans into traces."""
        client, collector, tracer = server_with_data
        
        # Get traces via server
        response = client.get('/api/traces')
        traces = json.loads(response.data)['traces']
        
        # Should have 2 traces
        assert len(traces) == 2
        
        trace_ids = {t['trace_id'] for t in traces}
        assert 'trace_001' in trace_ids
        assert 'trace_002' in trace_ids
    
    def test_server_filtering_integration(self, server_with_data):
        """Verify server filtering works with complex queries."""
        client, collector, tracer = server_with_data
        
        # Filter trace_001 with errors
        response = client.get('/api/spans?trace_id=trace_001&error=true')
        spans = json.loads(response.data)['spans']
        
        # Verify results
        assert len(spans) == 1
        assert spans[0]['trace_id'] == 'trace_001'
        assert spans[0]['attributes']['error'] == 'true'


class TestMultipleCollectorsIntegration:
    """Test tracing with multiple collectors."""
    
    def test_multi_collector_routing(self):
        """Verify spans sent to multiple collectors."""
        from collector.base import MultiCollector
        
        collector1 = MemoryCollector()
        collector2 = MemoryCollector()
        multi = MultiCollector([collector1, collector2])
        
        tracer = Tracer(collector=multi)
        
        # Create spans
        for i in range(3):
            span = tracer.start_span(f"op_{i}")
            span.finish()
        
        # Both collectors should have spans
        assert len(collector1.spans) == 3
        assert len(collector2.spans) == 3
    
    def test_batch_collector_with_tracer(self):
        """Verify batch collector works with tracer."""
        collector = BatchMemoryCollector(batch_size=2)
        tracer = Tracer(collector=collector)
        
        # Create spans
        for i in range(3):
            span = tracer.start_span(f"op_{i}")
            span.finish()
        
        # Verify batching
        # After 2 spans, first batch should be flushed
        assert len(collector.flushed_batches) >= 1
        # Third span should be in current batch or flushed
        total_spans = sum(len(batch) for batch in collector.flushed_batches) + len(collector.current_batch)
        assert total_spans == 3
    
    def test_query_across_multiple_sources(self):
        """Verify Query API works across multiple data sources."""
        # Create data in multiple collectors
        collector1 = MemoryCollector()
        collector2 = MemoryCollector()
        
        tracer1 = Tracer(collector=collector1)
        tracer2 = Tracer(collector=collector2)
        
        # Data in collector1
        span1 = tracer1.start_span("database_query", trace_id="trace_1")
        span1.finish()
        
        # Data in collector2
        span2 = tracer2.start_span("database_query", trace_id="trace_2")
        span2.finish()
        
        # Query each separately
        results1 = Query(collector1).by_name("database_query").execute()
        results2 = Query(collector2).by_name("database_query").execute()
        
        assert len(results1) == 1
        assert len(results2) == 1
        assert results1[0].trace_id != results2[0].trace_id


class TestEndToEndServerFlow:
    """Test complete flow from tracing to server API."""
    
    def test_trace_persist_query_retrieve(self):
        """Verify complete lifecycle: trace -> persist -> query -> retrieve."""
        # Create and populate
        collector = MemoryCollector()
        tracer = Tracer(collector=collector)
        
        trace_id = "complete_flow_trace"
        with tracer.start_span("parent", trace_id=trace_id) as parent:
            with tracer.start_span("child_1") as child1:
                child1.add_event("event_1")
                child1.finish()
            
            with tracer.start_span("child_2") as child2:
                child2.add_event("event_2")
                child2.finish()
        
        # Create server and query
        app = create_app(collector)
        app.config['TESTING'] = True
        client = app.test_client()
        
        # Query via API
        response = client.get(f'/api/traces/{trace_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        spans = data['trace']
        
        # Verify complete trace retrieved
        assert len(spans) == 3
        span_names = {s['name'] for s in spans}
        assert span_names == {'parent', 'child_1', 'child_2'}
        
        # Verify events persisted
        child1_span = next(s for s in spans if s['name'] == 'child_1')
        assert len(child1_span['events']) == 1
        assert child1_span['events'][0]['name'] == 'event_1'
    
    def test_metrics_api_end_to_end(self):
        """Verify metrics API works with real traced data."""
        collector = MemoryCollector()
        tracer = Tracer(collector=collector)
        
        # Create diverse spans
        for i in range(5):
            span = tracer.start_span("successful_op")
            span.finish()
        
        for i in range(2):
            span = tracer.start_span("failed_op")
            span.attributes["error"] = "true"
            span.finish()
        
        # Get metrics via API
        app = create_app(collector)
        app.config['TESTING'] = True
        client = app.test_client()
        
        response = client.get('/api/metrics')
        metrics = json.loads(response.data)
        
        # Verify metrics
        assert metrics['total_spans'] == 7
        assert metrics['error_count'] == 2
        assert metrics['error_rate'] == pytest.approx(2/7, abs=0.01)
        assert metrics['operations']['successful_op'] == 5
        assert metrics['operations']['failed_op'] == 2
