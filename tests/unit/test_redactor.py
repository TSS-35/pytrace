"""Tests for span redaction and PII masking."""
import pytest
from pytrace.redactor import Redactor, RedactionPattern


class TestRedactorBasics:
    """Test basic redaction functionality."""
    
    def test_redactor_initialization(self):
        """Redactor should initialize with patterns."""
        redactor = Redactor(patterns=["password", "api_key", "secret"])
        assert redactor is not None
    
    def test_redact_simple_string_attribute(self):
        """Should redact attribute values matching pattern."""
        redactor = Redactor(patterns=["password"])
        
        # Redact a simple dict
        data = {"password": "super_secret_123"}
        redacted = redactor.redact(data)
        
        # Original should be unchanged
        assert data["password"] == "super_secret_123"
        # Redacted should have masked value
        assert redacted["password"] != "super_secret_123"
        assert "REDACTED" in redacted["password"]
    
    def test_redact_nested_attributes(self):
        """Should redact nested attribute values."""
        redactor = Redactor(patterns=["password"])
        
        data = {
            "user": {"password": "secret"},
            "admin": {"password": "admin_secret"}
        }
        redacted = redactor.redact(data)
        
        assert "REDACTED" in redacted["user"]["password"]
        assert "REDACTED" in redacted["admin"]["password"]
    
    def test_preserve_non_matching_attributes(self):
        """Should not redact attributes not matching patterns."""
        redactor = Redactor(patterns=["password"])
        
        data = {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "secret123"
        }
        redacted = redactor.redact(data)
        
        # Non-matching should be unchanged
        assert redacted["username"] == "john_doe"
        assert redacted["email"] == "john@example.com"
        # Matching should be redacted
        assert "REDACTED" in redacted["password"]
    
    def test_redact_with_multiple_patterns(self):
        """Should redact multiple pattern types."""
        redactor = Redactor(patterns=["password", "api_key", "token"])
        
        data = {
            "password": "pass123",
            "api_key": "sk-1234567890",
            "token": "eyJhbGc...",
            "username": "john"
        }
        redacted = redactor.redact(data)
        
        assert "REDACTED" in redacted["password"]
        assert "REDACTED" in redacted["api_key"]
        assert "REDACTED" in redacted["token"]
        assert redacted["username"] == "john"
    
    def test_redact_case_insensitive(self):
        """Redaction patterns should be case-insensitive."""
        redactor = Redactor(patterns=["password"])
        
        data = {
            "password": "secret1",
            "PASSWORD": "secret2",
            "Password": "secret3"
        }
        redacted = redactor.redact(data)
        
        assert "REDACTED" in redacted["password"]
        assert "REDACTED" in redacted["PASSWORD"]
        assert "REDACTED" in redacted["Password"]
    
    def test_redact_with_regex_patterns(self):
        """Should support regex patterns for matching keys."""
        # Pattern to match keys containing "card" or "secret"
        redactor = Redactor(patterns=[r".*card.*", r".*secret.*"])
        
        data = {
            "card_number": "4532015112830366",
            "secret_key": "my_secret",
            "amount": "99.99"
        }
        redacted = redactor.redact(data)
        
        assert "REDACTED" in redacted["card_number"]
        assert "REDACTED" in redacted["secret_key"]
        assert redacted["amount"] == "99.99"
    
    def test_redact_partial_key_match(self):
        """Should redact based on partial key matches."""
        redactor = Redactor(patterns=["secret", "token", "key"])
        
        data = {
            "secret_key": "value1",
            "api_secret": "value2",
            "auth_token": "value3",
            "username": "value4"
        }
        redacted = redactor.redact(data)
        
        assert "REDACTED" in redacted["secret_key"]
        assert "REDACTED" in redacted["api_secret"]
        assert "REDACTED" in redacted["auth_token"]
        assert redacted["username"] == "value4"
    
    def test_custom_redaction_value(self):
        """Should support custom redaction replacement."""
        redactor = Redactor(patterns=["password"], redaction_value="[MASKED]")
        
        data = {"password": "secret"}
        redacted = redactor.redact(data)
        
        assert redacted["password"] == "[MASKED]"
    
    def test_redact_empty_dict(self):
        """Should handle empty dictionaries."""
        redactor = Redactor(patterns=["password"])
        data = {}
        redacted = redactor.redact(data)
        
        assert redacted == {}
    
    def test_redact_non_string_values(self):
        """Should handle non-string values gracefully."""
        redactor = Redactor(patterns=["password"])
        
        data = {
            "password": "secret",
            "count": 42,
            "ratio": 3.14,
            "enabled": True,
            "value": None
        }
        redacted = redactor.redact(data)
        
        assert "REDACTED" in redacted["password"]
        assert redacted["count"] == 42
        assert redacted["ratio"] == 3.14
        assert redacted["enabled"] is True
        assert redacted["value"] is None
    
    def test_redact_list_values(self):
        """Should handle list values in attributes."""
        redactor = Redactor(patterns=["password"])
        
        data = {
            "passwords": ["secret1", "secret2"],
            "usernames": ["alice", "bob"]
        }
        redacted = redactor.redact(data)
        
        # Lists should be redacted if key matches
        for item in redacted["passwords"]:
            assert "REDACTED" in item
        assert redacted["usernames"] == ["alice", "bob"]


class TestRedactionPatterns:
    """Test RedactionPattern configuration."""
    
    def test_pattern_creation(self):
        """Should create RedactionPattern objects."""
        pattern = RedactionPattern(name="password", pattern="password")
        assert pattern.name == "password"
        assert pattern.pattern == "password"
    
    def test_pattern_with_custom_value(self):
        """Should support custom redaction values per pattern."""
        pattern = RedactionPattern(
            name="credit_card",
            pattern=r"^\d{4}",
            redaction_value="****"
        )
        assert pattern.redaction_value == "****"


class TestRedactorEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_patterns(self):
        """Redactor with no patterns should not redact anything."""
        redactor = Redactor(patterns=[])
        
        data = {"password": "secret", "username": "john"}
        redacted = redactor.redact(data)
        
        assert redacted == data
    
    def test_none_patterns(self):
        """Redactor with None patterns should not fail."""
        redactor = Redactor(patterns=None)
        
        data = {"username": "john"}
        redacted = redactor.redact(data)
        
        assert redacted == data
    
    def test_invalid_regex_pattern(self):
        """Should treat invalid regex patterns as literal strings."""
        # Invalid regex like "[invalid(" gets treated as literal substring
        redactor = Redactor(patterns=[r"[invalid("])
        
        # The pattern should be treated as literal string match
        # So it will match keys containing "[invalid("
        data = {
            "[invalid(": "value1",
            "normal": "value2"
        }
        redacted = redactor.redact(data)
        
        # The bracketed key should be redacted
        assert "REDACTED" in redacted["[invalid("]
        assert redacted["normal"] == "value2"
    
    def test_special_characters_in_pattern(self):
        """Should handle special characters in pattern keys."""
        redactor = Redactor(patterns=["api-key", "access.token"])
        
        data = {
            "api-key": "secret1",
            "access.token": "secret2"
        }
        redacted = redactor.redact(data)
        
        assert "REDACTED" in redacted["api-key"]
        assert "REDACTED" in redacted["access.token"]
    
    def test_unicode_handling(self):
        """Should handle unicode characters."""
        redactor = Redactor(patterns=["パスワード", "密码"])  # password in Japanese/Chinese
        
        data = {
            "パスワード": "秘密",
            "密码": "secret",
            "username": "user"
        }
        redacted = redactor.redact(data)
        
        assert "REDACTED" in redacted["パスワード"]
        assert "REDACTED" in redacted["密码"]
        assert redacted["username"] == "user"
