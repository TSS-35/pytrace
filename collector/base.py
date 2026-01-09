from abc import ABC, abstractmethod
from pytrace.span import Span

class BaseCollector(ABC):
    @abstractmethod
    def send_span(self, span: Span) -> None:
        """Process a single span."""
        pass

class MultiCollector(BaseCollector):
    def __init__(self, collectors: list[BaseCollector]):
        self.collectors = collectors

    def send_span(self, span: Span) -> None:
        """Dispatches the span to all contained collectors."""
        for collector in self.collectors:
            collector.send_span(span)