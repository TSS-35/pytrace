import sqlite3
import json
from collector.base import BaseCollector
from pytrace.span import Span

class SQLiteCollector(BaseCollector):
    def __init__(self, db_path: str = "pytrace.db"):
        self.db_path = db_path
        self._create_table()

    def _create_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS spans (
                    span_id TEXT PRIMARY KEY,
                    trace_id TEXT,
                    parent_id TEXT,
                    name TEXT,
                    start_time REAL,
                    end_time REAL,
                    duration REAL,
                    attributes TEXT
                )
            """)

    def send_span(self, span: Span):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO spans VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    span.span_id,
                    span.trace_id,
                    span.parent_id,
                    span.name,
                    span.start_time,
                    span.end_time,
                    span.duration,
                    json.dumps(span.attributes)
                )
            )