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
            
            return jsonify([_serialize_span(span) for span in spans])
        
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
                    'traceId': trace_id,
                    'spans': [_serialize_span(s) for s in spans],
                    'startTime': min(s.start_time for s in spans) if spans else 0,
                    'endTime': max(s.end_time for s in spans if s.end_time) if spans else 0,
                    'duration': duration,
                    'spanCount': len(spans),
                    'errorCount': sum(1 for s in spans if s.attributes.get('error') == 'true'),
                    'status': 'error' if has_error else 'success'
                })
            
            return jsonify(traces)
        
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    @app.route('/api/traces/<trace_id>', methods=['GET'])
    def get_trace(trace_id):
        """Get entire trace by trace_id."""
        query = Query(app.collector).by_trace_id(trace_id)
        spans = query.execute()
        
        if not spans:
            return jsonify({'error': 'Trace not found', 'message': f'No trace with ID {trace_id}'}), 404
        
        # Build full trace response with spans
        spans_list = [_serialize_span(span) for span in spans]
        return jsonify({
            'traceId': trace_id,
            'spans': spans_list,
            'startTime': min(s.start_time for s in spans) if spans else 0,
            'endTime': max(s.end_time for s in spans if s.end_time) if spans else 0,
            'duration': (max(s.end_time or 0 for s in spans) - min(s.start_time for s in spans)) * 1000 if spans else 0,
            'spanCount': len(spans),
            'errorCount': sum(1 for s in spans if s.attributes.get('error') == 'true')
        })
    
    @app.route('/api/operations', methods=['GET'])
    def list_operations():
        """List all operation names with counts and statistics."""
        operation_stats = {}
        
        for span in app.collector.spans:
            if span.name not in operation_stats:
                operation_stats[span.name] = {
                    'name': span.name,
                    'callCount': 0,
                    'totalDuration': 0,
                    'minDuration': float('inf'),
                    'maxDuration': 0,
                    'errorCount': 0
                }
            
            stats = operation_stats[span.name]
            stats['callCount'] += 1
            stats['totalDuration'] += span.duration
            stats['minDuration'] = min(stats['minDuration'], span.duration)
            stats['maxDuration'] = max(stats['maxDuration'], span.duration)
            
            if span.attributes.get('error') == 'true':
                stats['errorCount'] += 1
        
        # Calculate averages and error rates
        operations = []
        for op_name, stats in operation_stats.items():
            stats['avgDuration'] = stats['totalDuration'] / stats['callCount'] if stats['callCount'] > 0 else 0
            stats['minDuration'] = stats['minDuration'] if stats['minDuration'] != float('inf') else 0
            stats['errorRate'] = stats['errorCount'] / stats['callCount'] if stats['callCount'] > 0 else 0
            
            # Convert to milliseconds
            stats['avgDuration'] = round(stats['avgDuration'] * 1000, 2)
            stats['minDuration'] = round(stats['minDuration'] * 1000, 2)
            stats['maxDuration'] = round(stats['maxDuration'] * 1000, 2)
            
            operations.append(stats)
        
        return jsonify(operations)
    
    @app.route('/api/metrics/latency', methods=['GET'])
    def get_latency_metrics():
        """Get latency percentile metrics."""
        operation = request.args.get('operation')
        
        durations = []
        for span in app.collector.spans:
            if operation and span.name != operation:
                continue
            durations.append(span.duration * 1000)  # Convert to ms
        
        if not durations:
            durations = [0]
        
        durations.sort()
        
        def percentile(data, p):
            idx = int(len(data) * p / 100)
            return round(data[min(idx, len(data)-1)], 2)
        
        return jsonify({
            'p50': percentile(durations, 50),
            'p95': percentile(durations, 95),
            'p99': percentile(durations, 99),
            'min': round(min(durations), 2) if durations else 0,
            'max': round(max(durations), 2) if durations else 0,
            'avg': round(sum(durations) / len(durations), 2) if durations else 0
        }) if durations else jsonify({
            'p50': 0,
            'p95': 0,
            'p99': 0,
            'min': 0,
            'max': 0,
            'avg': 0
        })
    
    @app.route('/api/metrics/latency/slowest', methods=['GET'])
    def get_slowest_operations():
        """Get slowest operations."""
        limit = request.args.get('limit', default=10, type=int)
        
        operation_stats = {}
        
        for span in app.collector.spans:
            if span.name not in operation_stats:
                operation_stats[span.name] = {
                    'name': span.name,
                    'callCount': 0,
                    'avgDuration': 0,
                    'totalDuration': 0
                }
            
            stats = operation_stats[span.name]
            stats['callCount'] += 1
            stats['totalDuration'] += span.duration * 1000  # Convert to ms
        
        # Calculate averages and sort
        operations = []
        for op_name, stats in operation_stats.items():
            stats['avgDuration'] = round(stats['totalDuration'] / stats['callCount'], 2)
            operations.append(stats)
        
        operations.sort(key=lambda x: x['avgDuration'], reverse=True)
        
        return jsonify(operations[:limit])
    
    @app.route('/api/errors/stats', methods=['GET'])
    def get_error_stats():
        """Get error statistics."""
        total_spans = len(app.collector.spans)
        error_spans = [s for s in app.collector.spans if s.attributes.get('error') == 'true']
        error_count = len(error_spans)
        error_rate = error_count / total_spans if total_spans > 0 else 0
        
        # Count errors by operation
        errors_by_operation = {}
        for span in error_spans:
            if span.name not in errors_by_operation:
                errors_by_operation[span.name] = 0
            errors_by_operation[span.name] += 1
        
        unique_operations = len(errors_by_operation)
        
        return jsonify({
            'totalErrors': error_count,
            'errorRate': round(error_rate, 4),
            'uniqueOperations': unique_operations,
            'errorsByOperation': errors_by_operation
        })
    
    @app.route('/api/errors/recent', methods=['GET'])
    def get_recent_errors():
        """Get recent errors."""
        limit = request.args.get('limit', default=20, type=int)
        
        # Get error spans sorted by start_time (most recent first)
        error_spans = [s for s in app.collector.spans if s.attributes.get('error') == 'true']
        error_spans.sort(key=lambda s: s.start_time, reverse=True)
        
        errors = []
        for span in error_spans[:limit]:
            errors.append({
                'operationName': span.name,
                'errorMessage': span.attributes.get('error.type', 'Unknown error'),
                'stackTrace': span.attributes.get('error.stack', '')
            })
        
        return jsonify(errors)
    
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
        'spanId': span.span_id,
        'operationName': span.name,
        'traceId': span.trace_id,
        'parentId': span.parent_id,
        'startTime': span.start_time,
        'endTime': span.end_time,
        'duration': span.duration,
        'attributes': span.attributes,
        'events': span.events
    }


if __name__ == '__main__':
    from collector.memory import MemoryCollector
    
    collector = MemoryCollector()
    app = create_app(collector)
    app.run(debug=True, port=5000)
