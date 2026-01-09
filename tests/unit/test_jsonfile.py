import os
import json
import pytest
from collector.jsonfile import JSONFileCollector
from pytrace.span import Span

FILE_PATH = "traces.json"

@pytest.fixture
def collector():
    # Setup: Ensure clean file
    if os.path.exists(FILE_PATH):
        os.remove(FILE_PATH)
    coll = JSONFileCollector(file_path=FILE_PATH)
    yield coll
    # Teardown
    if os.path.exists(FILE_PATH):
        os.remove(FILE_PATH)

def test_json_collector_saves_span(collector):
    span = Span(name="io-op", trace_id="t-555")
    span.finish()
    
    collector.send_span(span)
    
    # Verify the file content
    assert os.path.exists(FILE_PATH)
    with open(FILE_PATH, "r") as f:
        data = json.load(f)
    
    assert len(data) == 1
    assert data[0]["name"] == "io-op"
    assert data[0]["trace_id"] == "t-555"
    assert data[0]["duration"] is not None