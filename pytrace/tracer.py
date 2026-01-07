import uuid
import contextvars
from typing import Optional
from pytrace.span import Span

_active_span_var = contextvars.ContextVar("active_span", default=None)

class Tracer:
    @property
    def active_span(self) -> Optional[Span]:
        """Return the currently active span."""
        return _active_span_var.get()
    
    def start_span(self, name: str, trace_id: Optional[str] = None, parent_id: Optional[str] = None, attributes: Optional[dict] = None) -> Span:
        """Start a new span, automatically linking to the active parent."""
        parent = self.active_span

        if trace_id is None:
            trace_id = parent.trace_id if parent else uuid.uuid4().hex

        if parent_id is None and parent:
            parent_id = parent.span_id
        
        span = Span(
            name=name,
            trace_id=trace_id,
            parent_id=parent_id,
            attributes=attributes or {}
        )
        return span