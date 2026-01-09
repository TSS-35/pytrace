from abc import ABC, abstractmethod
from pytrace.span import Span

class BaseCollector(ABC):
    @abstractmethod
    def send_span(self, span: Span) -> None:
        """Process a single span."""
        pass