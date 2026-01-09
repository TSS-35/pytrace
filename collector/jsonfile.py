import json
import os
from collector.base import BaseCollector
from pytrace.span import Span

class JSONFileCollector(BaseCollector):
    def __init__(self, file_path: str = "traces.json"):
        self.file_path = file_path
        # Initialize file with empty list if it doesn't exist
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                json.dump([], f)

    def send_span(self, span: Span) -> None:
        """Appends a span to the JSON file."""
        span_data = {
            "span_id": span.span_id,
            "trace_id": span.trace_id,
            "parent_id": span.parent_id,
            "name": span.name,
            "start_time": span.start_time,
            "end_time": span.end_time,
            "duration": span.duration,
            "attributes": span.attributes
        }

        # Read, append, and write back
        with open(self.file_path, "r+") as f:
            data = json.load(f)
            data.append(span_data)
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()