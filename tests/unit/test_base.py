import pytest
from collector.base import BaseCollector, MultiCollector
from pytrace.span import Span
from unittest.mock import MagicMock

def test_cannot_instantiate_base_collector():
    """Verify that BaseCollector cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseCollector()

def test_subclass_must_implement_send_span():
    """Verify that a subclass must implement send_span."""
    class IncompleteCollector(BaseCollector):
        pass
        
    with pytest.raises(TypeError):
        IncompleteCollector()

def test_multi_collector_dispatches_to_all():
    # Create mock collectors
    mock_1 = MagicMock(spec=BaseCollector)
    mock_2 = MagicMock(spec=BaseCollector)
    
    multi = MultiCollector([mock_1, mock_2])
    span = Span(name="multi-test", trace_id="t1")
    
    multi.send_span(span)
    
    # Verify both mocks received the span
    mock_1.send_span.assert_called_once_with(span)
    mock_2.send_span.assert_called_once_with(span)

def test_multi_collector_handles_empty_list():
    multi = MultiCollector([])
    span = Span(name="empty-test", trace_id="t1")
    
    # Should not raise an error
    multi.send_span(span)