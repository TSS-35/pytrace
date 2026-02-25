"""HTTP API server for pytrace."""
from flask import Flask, jsonify, request
from pytrace.query import Query
from datetime import datetime, timezone
from typing import Dict, List, Any


def create_app(collector):
    """Create and configure Flask app with pytrace API."""
    app = Flask(__name__)
    app.config['JSON_SORT_KEYS'] = False
    
    # Store collector in app context
    app.collector = collector
    
    @app.route('/api/health', methods=['GET'])
    def health():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    @app.route('/api/spans', methods=['GET'])
    def get_spans():
        """Get spans with optional filtering and pagination."""
        try:
            # Get query parameters
            trace_id = request.args.get('trace_id')
            name = request.args.get('name')
            error = request.args.get('error', '').lower() == 'true'
            sort = request.args.get('sort', 'start_time')
            order = request.args.get('order', 'asc')
            limit = request.args.get('limit', type=int)
            offset = request.args.get('offset', type=int)
            
            # Build query
            query = Query(app.collector)
            
            if trace_id:
                query = query.by_trace_id(trace_id)
            if name:
                query = query.by_name(name)
            if error:
                query = query.with_errors()
            
            # Apply sorting
            if sort == 'duration':
                query = query.sort_by_duration(order)
            elif sort == 'name':
                query = query.sort_by_name(order)
            else:
                query = query.sort_by_start_time(order)
            
            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            # Execute query
            spans = query.execute()
            
            return jsonify({
                'spans': [_serialize_span(span) for span in spans],
                'count': len(spans)
            })
        
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    @app.route('/api/spans/<span_id>', methods=['GET'])
    def get_span(span_id):
        """Get specific span by ID."""
        for span in app.collector.spans:
            if span.span_id == span_id:
                return jsonify({'span': _serialize_span(span)})
        
        return jsonify({'error': 'Span not found', 'message': f'No span with ID {span_id}'}), 404
    
    @app.route('/api/traces', methods=['GET'])
    def list_traces():
        """List all traces with optional filtering."""
        try:
            error = request.args.get('error', '').lower() == 'true'
            
            # Group spans by trace_id
            traces_dict = {}
            for span in app.collector.spans:
                if span.trace_id not in traces_dict:
                    traces_dict[span.trace_id] = []
                traces_dict[span.trace_id].append(span)
            
            # Build trace summaries
            traces = []
            for trace_id, spans in traces_dict.items():
                has_error = any(s.attributes.get('error') == 'true' for s in spans)
                
                if error and not has_error:
                    continue
                
                # Calculate trace duration
                start_times = [s.start_time for s in spans]
                end_times = [s.end_time for s in spans if s.end_time]
                
                if start_times and end_times:
                    duration = (max(end_times) - min(start_times)) * 1000
                else:
                    duration = None
                
                traces.append({
                    'trace_id': trace_id,
                    'span_count': len(spans),
                    'duration': duration,
                    'error_count': sum(1 for s in spans if s.attributes.get('error') == 'true'),
                    'status': 'error' if has_error else 'success'
                })
            
            return jsonify({'traces': traces, 'count': len(traces)})
        
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    @app.route('/api/traces/<trace_id>', methods=['GET'])
    def get_trace(trace_id):
        """Get entire trace by trace_id."""
        query = Query(app.collector).by_trace_id(trace_id)
        spans = query.execute()
        
        if not spans:
            return jsonify({'error': 'Trace not found', 'message': f'No trace with ID {trace_id}'}), 404
        
        return jsonify({
            'trace': [_serialize_span(span) for span in spans],
            'count': len(spans)
        })
    
    @app.route('/api/operations', methods=['GET'])
    def list_operations():
        """List all operation names with counts."""
        operation_counts = {}
        
        for span in app.collector.spans:
            if span.name not in operation_counts:
                operation_counts[span.name] = 0
            operation_counts[span.name] += 1
        
        operations = [
            {'name': name, 'count': count}
            for name, count in sorted(operation_counts.items())
        ]
        
        return jsonify({'operations': operations, 'count': len(operations)})
    
    @app.route('/api/metrics', methods=['GET'])
    def get_metrics():
        """Get overall metrics and statistics."""
        from pytrace.tracer import Tracer
        
        # Create a temporary tracer to use its metrics methods
        tracer = Tracer()
        tracer._spans = app.collector.spans
        
        stats = tracer.duration_stats()
        
        return jsonify({
            'total_spans': tracer.span_count(),
            'error_count': tracer.error_count(),
            'error_rate': tracer.error_rate(),
            'duration_stats': {
                'min_ms': stats.get('min'),
                'max_ms': stats.get('max'),
                'avg_ms': stats.get('avg'),
                'count': stats.get('count')
            },
            'operations': tracer.span_counts_by_name()
        })
    
    return app


def _serialize_span(span) -> Dict[str, Any]:
    """Convert span to JSON-serializable dictionary."""
    return {
        'span_id': span.span_id,
        'name': span.name,
        'trace_id': span.trace_id,
        'parent_id': span.parent_id,
        'start_time': span.start_time,
        'end_time': span.end_time,
        'duration': span.duration,
        'attributes': span.attributes,
        'events': span.events
    }


if __name__ == '__main__':
    from collector.memory import MemoryCollector
    
    collector = MemoryCollector()
    app = create_app(collector)
    app.run(debug=True, port=5000)
