"""Integration tests for span redaction."""
import pytest
from pytrace.config import Config
from pytrace.tracer import Tracer
from pytrace.redactor import Redactor
from collector.memory import MemoryCollector


class TestRedactionIntegrationScenarios:
    """Integration tests for realistic redaction scenarios."""
    
    def test_user_authentication_flow(self):
        """Redact sensitive data from authentication flow."""
        patterns = ["password", "token", "secret"]
        redactor = Redactor(patterns=patterns)
        config = Config(redactor=redactor)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        # Simulate login flow
        with tracer.start_span("login_request") as span:
            span.attributes["username"] = "alice"
            span.attributes["password"] = "p@ssw0rd123"
            
            with tracer.start_span("validate_credentials") as child:
                child.attributes["password"] = "p@ssw0rd123"
                child.attributes["password_hash_match"] = "true"
        
        with tracer.start_span("issue_token") as span:
            span.attributes["token"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            span.attributes["expiry"] = "3600"
        
        # Verify sensitive data is redacted
        for span in collector.spans:
            for key, value in span.attributes.items():
                if key in patterns:
                    assert "REDACTED" in value, f"{key} should be redacted"
                else:
                    # Non-sensitive fields preserved
                    if key in ["username", "password_hash_match", "expiry"]:
                        assert value != "REDACTED"
    
    def test_database_query_with_sensitive_data(self):
        """Redact sensitive data in database operations."""
        patterns = ["password", "ssn", "credit_card", "api_key"]
        redactor = Redactor(patterns=patterns)
        config = Config(redactor=redactor)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        with tracer.start_span("database_insert") as span:
            span.attributes["table"] = "users"
            span.attributes["user_id"] = "12345"
            span.attributes["email"] = "user@example.com"
            span.attributes["password"] = "hashed_password"
            span.attributes["ssn"] = "123-45-6789"
            span.add_event("row_inserted", attributes={
                "row_count": 1,
                "credit_card": "****-****-****-1234"
            })
        
        collected_span = collector.spans[0]
        
        # Verify redaction
        assert "REDACTED" in collected_span.attributes["password"]
        assert "REDACTED" in collected_span.attributes["ssn"]
        assert collected_span.attributes["table"] == "users"
        assert collected_span.attributes["email"] == "user@example.com"
        
        # Check event redaction
        for event in collected_span.events:
            if "credit_card" in event["attributes"]:
                assert "REDACTED" in event["attributes"]["credit_card"]
    
    def test_api_call_with_credentials(self):
        """Redact API credentials from span attributes."""
        patterns = ["api_key", "api_secret", "bearer_token", "auth"]
        redactor = Redactor(patterns=patterns)
        config = Config(redactor=redactor)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        with tracer.start_span("external_api_call") as span:
            span.attributes["endpoint"] = "https://api.example.com/users"
            span.attributes["method"] = "POST"
            span.attributes["api_key"] = "sk_live_abc123"
            span.attributes["api_secret"] = "secret_xyz789"
            span.attributes["bearer_token"] = "Bearer eyJhbGc..."
            span.add_event("response_received", attributes={
                "status": "200",
                "auth": "Bearer eyJhbGc..."
            })
        
        collected_span = collector.spans[0]
        
        # Credentials redacted
        assert "REDACTED" in collected_span.attributes["api_key"]
        assert "REDACTED" in collected_span.attributes["api_secret"]
        assert "REDACTED" in collected_span.attributes["bearer_token"]
        
        # Metadata preserved
        assert collected_span.attributes["endpoint"] == "https://api.example.com/users"
        assert collected_span.attributes["method"] == "POST"
        
        # Event credentials redacted
        assert "REDACTED" in collected_span.events[0]["attributes"]["auth"]
        assert collected_span.events[0]["attributes"]["status"] == "200"
    
    def test_redaction_with_sampling(self):
        """Redaction and sampling work together."""
        from pytrace.sampler import ProbabilitySampler
        
        sampler = ProbabilitySampler(1.0)  # Always sample for testing
        redactor = Redactor(patterns=["password"])
        
        config = Config(sampler=sampler, redactor=redactor)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        # Create spans with sensitive data
        for i in range(10):
            with tracer.start_span(f"operation_{i}") as span:
                span.attributes["password"] = f"secret_{i}"
        
        # All should be collected and redacted
        assert len(collector.spans) == 10
        for span in collector.spans:
            assert "REDACTED" in span.attributes["password"]
    
    def test_nested_redaction_in_complex_trace(self):
        """Test redaction in complex nested trace."""
        patterns = ["secret", "token"]
        redactor = Redactor(patterns=patterns)
        config = Config(redactor=redactor)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        with tracer.start_span("request") as req:
            req.attributes["secret_id"] = "secret_123"
            
            with tracer.start_span("authenticate") as auth:
                auth.attributes["secret_key"] = "key_abc"
                auth.add_event("auth_check", attributes={
                    "token": "jwt_token",
                    "valid": "true"
                })
                
                with tracer.start_span("fetch_user") as fetch:
                    fetch.attributes["secret_data"] = "sensitive_info"
                    fetch.attributes["user_id"] = "user_123"
        
        # Verify all redactions across the trace
        redacted_count = 0
        for span in collector.spans:
            for key, value in span.attributes.items():
                if any(p in key.lower() for p in patterns):
                    assert "REDACTED" in value, f"{span.name}.{key} should be redacted"
                    redacted_count += 1
            
            for event in span.events:
                for key, value in event["attributes"].items():
                    if any(p in key.lower() for p in patterns):
                        assert "REDACTED" in value, f"{span.name}.event.{key} should be redacted"
                        redacted_count += 1
        
        assert redacted_count > 0, "Should have redacted some fields"
    
    def test_no_redaction_when_disabled(self):
        """Sensitive data preserved when redaction disabled."""
        config = Config(redactor=Redactor(patterns=[]))  # Empty patterns = no redaction
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        with tracer.start_span("operation") as span:
            span.attributes["password"] = "secret123"
            span.attributes["api_key"] = "key_xyz"
        
        collected_span = collector.spans[0]
        
        # Sensitive data NOT redacted
        assert collected_span.attributes["password"] == "secret123"
        assert collected_span.attributes["api_key"] == "key_xyz"
    
    def test_custom_redaction_value(self):
        """Test custom redaction replacement value."""
        redactor = Redactor(patterns=["secret"], redaction_value="[CENSORED]")
        config = Config(redactor=redactor)
        collector = MemoryCollector()
        tracer = Tracer(config=config, collector=collector)
        
        with tracer.start_span("test") as span:
            span.attributes["secret_id"] = "secret_123"
            span.attributes["public_id"] = "public_456"
        
        collected_span = collector.spans[0]
        
        assert collected_span.attributes["secret_id"] == "[CENSORED]"
        assert collected_span.attributes["public_id"] == "public_456"
