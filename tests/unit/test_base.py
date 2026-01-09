import pytest
from collector.base import BaseCollector

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