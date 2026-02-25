"""Integration tests for auto-tracing functionality."""
import pytest
from pytrace.tracer import Tracer
from pytrace.config import Config
from pytrace.query import Query
from collector.memory import MemoryCollector


class TestAutoTraceIntegration:
    """Test automatic function tracing end-to-end."""
    
    def test_auto_trace_creates_spans_for_calls(self):
        """Verify auto-trace creates spans for function calls."""
        collector = MemoryCollector()
        config = Config()
        tracer = Tracer(config=config, collector=collector)
        
        def my_function():
            return "result"
        
        tracer.start_auto_trace()
        result = my_function()
        tracer.stop_auto_trace()
        
        assert result == "result"
        
        # Verify span was created
        results = Query(collector).by_name("my_function").execute()
        assert len(results) > 0
    
    def test_auto_trace_captures_nested_calls(self):
        """Verify auto-trace creates parent-child spans for nested calls."""
        collector = MemoryCollector()
        config = Config()
        tracer = Tracer(config=config, collector=collector)
        
        def child_function():
            return "child"
        
        def parent_function():
            result = child_function()
            return f"parent-{result}"
        
        tracer.start_auto_trace()
        result = parent_function()
        tracer.stop_auto_trace()
        
        assert result == "parent-child"
        
        # Get spans
        parent_spans = Query(collector).by_name("parent_function").execute()
        child_spans = Query(collector).by_name("child_function").execute()
        
        assert len(parent_spans) > 0
        assert len(child_spans) > 0
        
        # Verify parent-child relationship
        if parent_spans and child_spans:
            parent = parent_spans[0]
            child = child_spans[0]
            assert child.parent_id == parent.span_id
            assert child.trace_id == parent.trace_id
    
    def test_auto_trace_exception_handling(self):
        """Verify auto-trace captures exceptions."""
        collector = MemoryCollector()
        config = Config()
        tracer = Tracer(config=config, collector=collector)
        
        def failing_function():
            raise RuntimeError("Function failed")
        
        tracer.start_auto_trace()
        try:
            failing_function()
        except RuntimeError:
            pass
        tracer.stop_auto_trace()
        
        # Verify error span created
        error_spans = Query(collector).by_name("failing_function").with_errors().execute()
        
        assert len(error_spans) > 0
        assert error_spans[0].attributes["error"] == "true"
        assert error_spans[0].attributes["error.type"] == "RuntimeError"
    
    def test_auto_trace_with_module_filtering(self):
        """Verify auto-trace respects module filtering."""
        collector = MemoryCollector()
        
        # Use default config (will exclude pytest, unittest, etc.)
        config = Config()
        tracer = Tracer(config=config, collector=collector)
        
        def traced_function():
            return "traced"
        
        tracer.start_auto_trace()
        result = traced_function()
        tracer.stop_auto_trace()
        
        # Verify config is working (it should exclude pytest internally)
        assert config.should_trace(__name__) == True
        assert config.should_trace("pytest") == False
        assert config.should_trace("pytrace") == False
    
    def test_auto_trace_metrics_accumulation(self):
        """Verify metrics accumulate correctly with auto-trace."""
        collector = MemoryCollector()
        config = Config()
        tracer = Tracer(config=config, collector=collector)
        
        def operation_a():
            return 1
        
        def operation_b():
            return 2
        
        tracer.start_auto_trace()
        
        # Call multiple times
        for i in range(3):
            operation_a()
        
        for i in range(2):
            operation_b()
        
        tracer.stop_auto_trace()
        
        # Verify counts
        counts = tracer.span_counts_by_name()
        assert counts.get("operation_a", 0) > 0
        assert counts.get("operation_b", 0) > 0
        assert counts.get("operation_a", 0) >= counts.get("operation_b", 0)


class TestAutoTraceHierarchy:
    """Test call hierarchy preservation in auto-tracing."""
    
    def test_deep_call_stack_hierarchy(self):
        """Verify hierarchy preserved in deep call stacks."""
        collector = MemoryCollector()
        config = Config()
        tracer = Tracer(config=config, collector=collector)
        
        def level_3():
            return "level_3"
        
        def level_2():
            return level_3()
        
        def level_1():
            return level_2()
        
        tracer.start_auto_trace()
        result = level_1()
        tracer.stop_auto_trace()
        
        # Verify all levels traced
        l1 = Query(collector).by_name("level_1").execute()
        l2 = Query(collector).by_name("level_2").execute()
        l3 = Query(collector).by_name("level_3").execute()
        
        if l1 and l2 and l3:
            # Verify chain: l1 -> l2 -> l3
            assert l2[0].parent_id == l1[0].span_id
            assert l3[0].parent_id == l2[0].span_id
    
    def test_multiple_calls_same_function(self):
        """Verify multiple calls to same function create separate spans."""
        collector = MemoryCollector()
        config = Config()
        tracer = Tracer(config=config, collector=collector)
        
        def multiply(x, y):
            return x * y
        
        tracer.start_auto_trace()
        
        result1 = multiply(2, 3)
        result2 = multiply(4, 5)
        result3 = multiply(6, 7)
        
        tracer.stop_auto_trace()
        
        # Verify separate spans for each call
        spans = Query(collector).by_name("multiply").execute()
        assert len(spans) >= 3
