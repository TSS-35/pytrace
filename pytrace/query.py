"""Query API for filtering and searching spans."""
from typing import List, Optional, Literal
from pytrace.span import Span


class Query:
    """Fluent query builder for filtering spans from a collector."""
    
    def __init__(self, collector):
        """Initialize query with a collector.
        
        Args:
            collector: A collector instance with spans attribute
        """
        self.collector = collector
        self._filters = []
        self._sort_key = None
        self._sort_order = "asc"
        self._limit_count = None
        self._offset_count = 0
    
    def by_trace_id(self, trace_id: str) -> "Query":
        """Filter spans by trace_id."""
        self._filters.append(("trace_id", trace_id))
        return self
    
    def by_name(self, name: str) -> "Query":
        """Filter spans by operation name."""
        self._filters.append(("name", name))
        return self
    
    def with_errors(self) -> "Query":
        """Filter to only spans with errors."""
        self._filters.append(("error", True))
        return self
    
    def by_duration_range(self, min_ms: float, max_ms: float) -> "Query":
        """Filter spans by duration range in milliseconds."""
        self._filters.append(("duration_range", (min_ms, max_ms)))
        return self
    
    def sort_by_duration(self, order: Literal["asc", "desc"] = "asc") -> "Query":
        """Sort results by span duration."""
        self._sort_key = "duration"
        self._sort_order = order
        return self
    
    def sort_by_start_time(self, order: Literal["asc", "desc"] = "asc") -> "Query":
        """Sort results by span start_time."""
        self._sort_key = "start_time"
        self._sort_order = order
        return self
    
    def sort_by_name(self, order: Literal["asc", "desc"] = "asc") -> "Query":
        """Sort results by span name."""
        self._sort_key = "name"
        self._sort_order = order
        return self
    
    def limit(self, count: int) -> "Query":
        """Limit results to count spans."""
        self._limit_count = count
        return self
    
    def offset(self, count: int) -> "Query":
        """Skip count spans in results."""
        if not isinstance(count, int):
            raise TypeError(f"offset count must be an integer, got {type(count).__name__}")
        if count < 0:
            raise ValueError(f"offset count must be non-negative, got {count}")
        self._offset_count = count
        return self
    
    def execute(self) -> List[Span]:
        """Execute query and return filtered spans."""
        results = self.collector.spans.copy()
        
        # Apply filters
        for filter_type, filter_value in self._filters:
            if filter_type == "trace_id":
                results = [s for s in results if s.trace_id == filter_value]
            elif filter_type == "name":
                results = [s for s in results if s.name == filter_value]
            elif filter_type == "error":
                results = [s for s in results if s.attributes.get("error") == "true"]
            elif filter_type == "duration_range":
                min_ms, max_ms = filter_value
                results = [s for s in results 
                          if s.duration is not None and min_ms <= s.duration <= max_ms]
        
        # Apply sorting
        if self._sort_key:
            reverse = self._sort_order == "desc"
            if self._sort_key == "duration":
                results = sorted(results, key=lambda s: s.duration or 0, reverse=reverse)
            elif self._sort_key == "start_time":
                results = sorted(results, key=lambda s: s.start_time, reverse=reverse)
            elif self._sort_key == "name":
                results = sorted(results, key=lambda s: s.name, reverse=reverse)
        
        # Apply offset and limit
        if self._offset_count > 0:
            results = results[self._offset_count:]
        
        if self._limit_count is not None:
            results = results[:self._limit_count]
        
        return results
    
    def count(self) -> int:
        """Execute query and return count of matching spans."""
        return len(self.execute())
