"""Tests for redacting spans and span attributes."""
import pytest
from pytrace.span import Span
from pytrace.config import Config
from pytrace.tracer import Tracer
from pytrace.redactor import Redactor
from collector.memory import MemoryCollector


class TestSpanRedaction:
    """Test redacting PII from spans."""
    
    def test_redactor_in_config(self):
        """Config should accept redactor instance."""
        redactor = Redactor(patterns=["password"])
        config = Config(redactor=redactor)
        
        assert config.redactor is redactor
    
    def test_redactor_default(self):
        """Config should have default no-op redactor."""
        config = Config()
        assert config.redactor is not None
    
    def test_tracer_applies_redaction_to_attributes(self):
        """Tracer should apply redaction to span attributes."""
        redactor = Redactor(patterns=["password"])
        config = Config(redactor=redactor)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        # Create span with sensitive attribute
        with tracer.start_span("login") as span:
            span.attributes["password"] = "super_secret"
            span.attributes["username"] = "john_doe"
        
        # Check collected span has redacted password
        assert len(collector.spans) == 1
        collected_span = collector.spans[0]
        
        assert "REDACTED" in collected_span.attributes["password"]
        assert collected_span.attributes["username"] == "john_doe"
    
    def test_redaction_applied_on_span_finish(self):
        """Redaction should happen when span finishes."""
        redactor = Redactor(patterns=["api_key"])
        config = Config(redactor=redactor)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        span = tracer.start_span("api_call")
        span.attributes["api_key"] = "sk-1234567890"
        span.attributes["endpoint"] = "/users"
        span.finish()
        
        # Redaction should have been applied during finish()
        assert "REDACTED" in span.attributes["api_key"]
        assert span.attributes["endpoint"] == "/users"
    
    def test_redact_event_attributes(self):
        """Should redact attributes in span events."""
        redactor = Redactor(patterns=["token"])
        config = Config(redactor=redactor)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        with tracer.start_span("auth") as span:
            span.add_event("token_generated", attributes={
                "token": "eyJhbGc...",
                "expiry": "3600"
            })
            span.add_event("token_verified", attributes={
                "token": "eyJhbGc...",
                "valid": True
            })
        
        collected_span = collector.spans[0]
        
        # Check both events have redacted tokens
        for event in collected_span.events:
            if "token" in event["attributes"]:
                assert "REDACTED" in event["attributes"]["token"]
            assert event["attributes"].get("expiry") == "3600" or event["attributes"].get("valid") is True
    
    def test_redaction_with_multiple_patterns(self):
        """Should apply multiple redaction patterns."""
        redactor = Redactor(patterns=["password", "api_key", "ssn"])
        config = Config(redactor=redactor)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        with tracer.start_span("user_signup") as span:
            span.attributes["password"] = "pass123"
            span.attributes["api_key"] = "sk-abc123"
            span.attributes["ssn"] = "123-45-6789"
            span.attributes["email"] = "user@example.com"
        
        collected_span = collector.spans[0]
        attrs = collected_span.attributes
        
        assert "REDACTED" in attrs["password"]
        assert "REDACTED" in attrs["api_key"]
        assert "REDACTED" in attrs["ssn"]
        assert attrs["email"] == "user@example.com"
    
    def test_no_redaction_without_patterns(self):
        """Should not redact if no patterns configured."""
        redactor = Redactor(patterns=[])
        config = Config(redactor=redactor)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        with tracer.start_span("operation") as span:
            span.attributes["password"] = "secret123"
        
        collected_span = collector.spans[0]
        assert collected_span.attributes["password"] == "secret123"
    
    def test_redaction_preserves_other_span_fields(self):
        """Redaction should not affect other span properties."""
        redactor = Redactor(patterns=["password"])
        config = Config(redactor=redactor)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        with tracer.start_span("test_op") as span:
            span.attributes["password"] = "secret"
            span.attributes["user_id"] = "123"
        
        collected_span = collector.spans[0]
        
        # Redaction only affects password
        assert "REDACTED" in collected_span.attributes["password"]
        assert collected_span.attributes["user_id"] == "123"
        # Other fields unchanged
        assert collected_span.name == "test_op"
        assert collected_span.trace_id is not None
        assert collected_span.span_id is not None
    
    def test_redaction_with_nested_events(self):
        """Should redact nested event attributes."""
        redactor = Redactor(patterns=["secret"])
        config = Config(redactor=redactor)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        with tracer.start_span("complex") as span:
            span.add_event("initialization", attributes={
                "secret_key": "confidential_data",
                "public_info": "visible"
            })
            span.add_event("completion", attributes={
                "secret_key": "another_secret",
                "status": "done"
            })
        
        collected_span = collector.spans[0]
        
        for event in collected_span.events:
            if "secret_key" in event["attributes"]:
                assert "REDACTED" in event["attributes"]["secret_key"]
            assert event["attributes"].get("public_info") == "visible" or event["attributes"].get("status") == "done"


class TestRedactionIntegration:
    """Integration tests for redaction with full tracer."""
    
    def test_redaction_with_child_spans(self):
        """Redaction should apply to parent and child spans."""
        redactor = Redactor(patterns=["password"])
        config = Config(redactor=redactor)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        with tracer.start_span("parent") as parent:
            parent.attributes["password"] = "parent_secret"
            
            with tracer.start_span("child") as child:
                child.attributes["password"] = "child_secret"
        
        assert len(collector.spans) == 2
        for span in collector.spans:
            assert "REDACTED" in span.attributes["password"]
    
    def test_redaction_with_errors(self):
        """Redaction should work with error attributes."""
        redactor = Redactor(patterns=["password"])
        config = Config(redactor=redactor)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        try:
            with tracer.start_span("risky_operation") as span:
                span.attributes["password"] = "secret"
                raise ValueError("Something went wrong")
        except ValueError:
            pass
        
        collected_span = collector.spans[0]
        
        # Password should be redacted even with error
        assert "REDACTED" in collected_span.attributes["password"]
        # Error should be recorded
        assert collected_span.attributes.get("error") == "true"
    
    def test_sensitive_data_examples(self):
        """Test real-world sensitive data patterns."""
        patterns = [
            "password",
            "api_key",
            "api_secret",
            "token",
            "ssn",
            "credit_card",
            "auth_token"
        ]
        redactor = Redactor(patterns=patterns)
        config = Config(redactor=redactor)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        with tracer.start_span("payment") as span:
            span.attributes["password"] = "user_password"
            span.attributes["api_key"] = "sk_test_123"
            span.attributes["api_secret"] = "secret_value"
            span.attributes["token"] = "jwt_token_xyz"
            span.attributes["ssn"] = "123-45-6789"
            span.attributes["credit_card"] = "4532-0151-1283-0366"
            span.attributes["auth_token"] = "bearer_token_abc"
            span.attributes["amount"] = "99.99"
            span.attributes["status"] = "completed"
        
        collected_span = collector.spans[0]
        attrs = collected_span.attributes
        
        # All sensitive fields redacted
        assert "REDACTED" in attrs["password"]
        assert "REDACTED" in attrs["api_key"]
        assert "REDACTED" in attrs["api_secret"]
        assert "REDACTED" in attrs["token"]
        assert "REDACTED" in attrs["ssn"]
        assert "REDACTED" in attrs["credit_card"]
        assert "REDACTED" in attrs["auth_token"]
        
        # Non-sensitive fields preserved
        assert attrs["amount"] == "99.99"
        assert attrs["status"] == "completed"
