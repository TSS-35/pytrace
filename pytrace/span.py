from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any
from time import time
import uuid

@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    parent_id: Optional[str] = None
    start_time: float = field(default_factory=time)
    end_time: Optional[float] = None
    attributes: Dict[str, str] = field(default_factory=dict)
    on_finish: Optional[Callable[['Span'], Any]] = field(default=None, repr=False)
    _token: Optional[Any] = field(default=None, repr=False)

    def finish(self):
        """Mark the span as finished and trigger the collector callback."""
        if self.end_time is None:
            self.end_time = time()
            if self.on_finish:
                self.on_finish(self)

    @property
    def duration(self) -> Optional[float]:
        """Calculate the duration of the span."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000  # duration in milliseconds
    
    def __enter__(self):
        """Allows usage as a context manager."""
        from pytrace.context import active_span_var
        self._token = active_span_var.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Automatically finishes the span when exiting the block."""
        from pytrace.context import active_span_var
        
        # Capture error details if an exception occurred
        if exc_type is not None:
            self.attributes["error"] = "true"
            self.attributes["error.type"] = exc_type.__name__
            self.attributes["error.message"] = str(exc_val)
            
        if self._token:
            active_span_var.reset(self._token)
        self.finish()
