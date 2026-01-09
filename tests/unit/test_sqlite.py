import os
import sqlite3
import pytest
from collector.sqlite import SQLiteCollector
from pytrace.span import Span

DB_PATH = "test_traces.db"

@pytest.fixture
def collector():
    # Setup: Ensure clean DB for the test
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    coll = SQLiteCollector(db_path=DB_PATH)
    yield coll
    # Teardown: Clean up
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def test_sqlite_collector_saves_span(collector):
    # 1. Create and finish a span
    span = Span(name="query-users", trace_id="t-100")
    span.finish()
    
    # 2. Save it
    collector.send_span(span)
    
    # 3. Verify persistence
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, trace_id, duration FROM spans")
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert row[0] == "query-users"
    assert row[1] == "t-100"
    assert row[2] is not None
