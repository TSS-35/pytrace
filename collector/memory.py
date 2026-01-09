from typing import List
from collector.base import BaseCollector
from pytrace.span import Span

class MemoryCollector(BaseCollector):
    def __init__(self):
        self.spans: List[Span] = []

    def send_span(self, span: Span) -> None:
        self.spans.append(span)

    def clear(self):
        self.spans = []