from typing import List
from collector.base import BaseCollector
from pytrace.span import Span
import threading
import time

class MemoryCollector(BaseCollector):
    def __init__(self):
        self.spans: List[Span] = []

    def send_span(self, span: Span) -> None:
        self.spans.append(span)

    def span_count(self) -> int:
        """Return the count of spans in memory."""
        return len(self.spans)

    def flush(self) -> List[Span]:
        """Flush all buffered spans and return them."""
        flushed = self.spans.copy()
        self.spans = []
        return flushed

    def clear(self):
        self.spans = []


class BatchMemoryCollector(BaseCollector):
    """Collects spans in batches with optional auto-flush on threshold or timer."""
    
    def __init__(self, batch_size: int = 10, flush_interval_ms: int = 0):
        """
        Initialize batch collector.
        
        Args:
            batch_size: Number of spans to accumulate before flushing
            flush_interval_ms: Auto-flush interval in milliseconds (0 = disabled)
        """
        self.batch_size = batch_size
        self.flush_interval_ms = flush_interval_ms
        self.current_batch: List[Span] = []
        self.flushed_batches: List[List[Span]] = []
        self._lock = threading.Lock()
        self._flush_timer = None
        self._stop_event = threading.Event()

    def send_span(self, span: Span) -> None:
        """Add span to current batch and flush if threshold reached."""
        with self._lock:
            self.current_batch.append(span)
            
            # Check if we should flush based on batch size
            if len(self.current_batch) >= self.batch_size:
                self._flush_batch()
            elif self.flush_interval_ms > 0 and not self._flush_timer:
                # Start timer if configured and not already running
                self._start_flush_timer()

    def _flush_batch(self):
        """Flush current batch (call with lock held)."""
        if self.current_batch:
            self.flushed_batches.append(self.current_batch.copy())
            self.current_batch = []

    def _start_flush_timer(self):
        """Start the auto-flush timer."""
        def flush_after_interval():
            time.sleep(self.flush_interval_ms / 1000.0)
            with self._lock:
                if not self._stop_event.is_set():
                    self._flush_batch()
        
        self._flush_timer = threading.Thread(target=flush_after_interval, daemon=True)
        self._flush_timer.start()

    def flush(self) -> List[Span]:
        """Manually flush current batch."""
        with self._lock:
            self._flush_batch()
            # Drain all flushed batches: flatten them and clear the buffer
            all_spans = [span for batch in self.flushed_batches for span in batch]
            self.flushed_batches = []
            return all_spans

    def clear(self):
        """Clear all batches."""
        with self._lock:
            self.current_batch = []
            self.flushed_batches = []