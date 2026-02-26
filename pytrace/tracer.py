import uuid
import sys
from typing import Optional, Dict, List
from pytrace.span import Span
from pytrace.context import active_span_var

class Tracer:
    def __init__(self, config=None, collector=None):
        self.config = config
        self.collector = collector
        self._active_tokens = {} # Maps span_id to context token
        self._is_tracing = False
        self._spans: List[Span] = []  # Track all spans for metrics

    @property
    def active_span(self) -> Optional[Span]:
        return active_span_var.get()
    
    def _create_noop_span(self, name: str, trace_id: str, parent_id: Optional[str], 
                          attributes: Dict) -> Span:
        """Create a no-op span that won't be collected.
        
        Used when sampling rejects a span.
        
        Args:
            name: Span name
            trace_id: Trace ID
            parent_id: Parent span ID
            attributes: Span attributes
            
        Returns:
            Span with on_finish=None (won't be collected)
        """
        return Span(
            name=name,
            trace_id=trace_id,
            parent_id=parent_id,
            attributes=attributes or {},
            on_finish=None  # Don't collect this span
        )

    def start_span(self, name: str, **kwargs) -> Span:
        parent = self.active_span
        trace_id = kwargs.get("trace_id") or (parent.trace_id if parent else uuid.uuid4().hex)
        parent_id = kwargs.get("parent_id") or (parent.span_id if parent else None)
        attributes = kwargs.get("attributes") or {}
        
        # Check sampling decision
        if self.config and self.config.sampler:
            sampler = self.config.sampler
            # Use requires_trace_id() method instead of fragile class name comparison
            should_sample = (
                sampler.should_sample(trace_id) 
                if sampler.requires_trace_id() 
                else sampler.should_sample()
            )
            
            if not should_sample:
                # Sampling rejected this span, return no-op span
                return self._create_noop_span(name, trace_id, parent_id, attributes)
        
        span = Span(
            name=name,
            trace_id=trace_id,
            parent_id=parent_id,
            attributes=kwargs.get("attributes") or {},
            on_finish=self.collector.send_span if self.collector else None,
            redactor=self.config.redactor if self.config else None
        )
        self._spans.append(span)  # Track for metrics
        return span

    def start_auto_trace(self):
        if not self._is_tracing:
            sys.settrace(self._trace_callback)
            self._is_tracing = True

    def stop_auto_trace(self):
        sys.settrace(None)
        self._is_tracing = False

    def _trace_callback(self, frame, event, arg):
        # 1. Check if we should even trace this module
        module_name = frame.f_globals.get("__name__", "")
        if self.config and not self.config.should_trace(module_name):
            return None

        func_name = frame.f_code.co_name

        if event == 'call':
            # Start a new span for the function call
            span = self.start_span(name=func_name)
            # Manually enter the context since we aren't using 'with'
            token = active_span_var.set(span)
            self._active_tokens[span.span_id] = token
            return self._trace_callback
        
        elif event == 'exception':
            # arg is a tuple: (exception_type, value, traceback)
            exc_type, exc_val, _ = arg
            span = self.active_span
            if span and span.name == func_name:
                span.attributes["error"] = "true"
                span.attributes["error.type"] = exc_type.__name__
                span.attributes["error.message"] = str(exc_val)

        elif event == 'return':
            # Finish the current span
            span = self.active_span
            if span and span.name == func_name:
                span.finish()
                # Clean up context
                token = self._active_tokens.pop(span.span_id, None)
                if token:
                    active_span_var.reset(token)

        return self._trace_callback

    # Metrics Methods
    def span_count(self) -> int:
        """Return the total number of spans created."""
        return len(self._spans)

    def error_count(self) -> int:
        """Return the count of spans with errors."""
        return sum(1 for span in self._spans if span.attributes.get("error") == "true")

    def error_rate(self) -> float:
        """Return the error rate as a fraction (0.0 to 1.0)."""
        if not self._spans:
            return 0.0
        return self.error_count() / len(self._spans)

    def duration_stats(self) -> Dict[str, float]:
        """Return duration statistics for all spans."""
        finished_spans = [s for s in self._spans if s.duration is not None]
        if not finished_spans:
            return {"count": 0, "min": 0, "max": 0, "avg": 0}
        
        durations = [s.duration for s in finished_spans]
        return {
            "count": len(durations),
            "min": min(durations),
            "max": max(durations),
            "avg": sum(durations) / len(durations)
        }

    def span_counts_by_name(self) -> Dict[str, int]:
        """Return span counts grouped by operation name."""
        counts: Dict[str, int] = {}
        for span in self._spans:
            counts[span.name] = counts.get(span.name, 0) + 1
        return counts

    def reset_metrics(self):
        """Clear all tracked spans and metrics."""
        self._spans = []

    # Trace Context Propagation Methods (for distributed tracing)
    def extract_context(self, span: Span) -> Dict:
        """Extract trace context from a span for propagation to other services."""
        return {
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "trace_flags": "01"  # Sampled
        }

    def inject_context(self, context: Dict, name: str, **kwargs) -> Span:
        """Create a span using injected context from another service."""
        trace_id = context.get("trace_id")
        parent_id = context.get("span_id")
        attributes = kwargs.get("attributes") or {}
        
        return self.start_span(
            name=name,
            trace_id=trace_id,
            parent_id=parent_id,
            attributes=attributes
        )

    def extract_as_http_headers(self, span: Span) -> Dict[str, str]:
        """Extract trace context in W3C Trace Context format for HTTP headers."""
        # Format: version-trace_id-span_id-trace_flags
        traceparent = f"00-{span.trace_id}-{span.span_id}-01"
        return {"traceparent": traceparent}

    def from_http_headers(self, headers: Dict[str, str], name: str, **kwargs) -> Span:
        """Create a span from W3C Trace Context HTTP headers."""
        traceparent = headers.get("traceparent", "")
        
        if traceparent:
            # Parse: version-trace_id-span_id-trace_flags
            parts = traceparent.split("-")
            if len(parts) >= 4:
                trace_id = parts[1]
                parent_id = parts[2]
                
                return self.start_span(
                    name=name,
                    trace_id=trace_id,
                    parent_id=parent_id,
                    **kwargs
                )
        
        # Fallback if no valid header
        return self.start_span(name=name, **kwargs)