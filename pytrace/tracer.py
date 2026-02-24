import uuid
import sys
from typing import Optional
from pytrace.span import Span
from pytrace.context import active_span_var

class Tracer:
    def __init__(self, config=None, collector=None):
        self.config = config
        self.collector = collector
        self._active_tokens = {} # Maps span_id to context token
        self._is_tracing = False

    @property
    def active_span(self) -> Optional[Span]:
        return active_span_var.get()

    def start_span(self, name: str, **kwargs) -> Span:
        parent = self.active_span
        trace_id = kwargs.get("trace_id") or (parent.trace_id if parent else uuid.uuid4().hex)
        parent_id = kwargs.get("parent_id") or (parent.span_id if parent else None)
        
        return Span(
            name=name,
            trace_id=trace_id,
            parent_id=parent_id,
            attributes=kwargs.get("attributes") or {},
            on_finish=self.collector.send_span if self.collector else None
        )

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