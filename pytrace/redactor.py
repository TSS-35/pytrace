"""Span redaction for masking sensitive data (PII, credentials, etc.)."""
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class RedactionPattern:
    """Configuration for a redaction pattern."""
    
    name: str
    pattern: str
    redaction_value: str = "***REDACTED***"
    is_regex: bool = False


class Redactor:
    """Redacts sensitive data from span attributes and events."""
    
    def __init__(
        self,
        patterns: Optional[List[str]] = None,
        redaction_value: str = "***REDACTED***",
        case_sensitive: bool = False
    ):
        """Initialize redactor with patterns.
        
        Args:
            patterns: List of pattern strings to match (substring or regex)
            redaction_value: Default value to replace matched content
            case_sensitive: Whether pattern matching is case-sensitive
        """
        self.patterns = patterns or []
        self.redaction_value = redaction_value
        self.case_sensitive = case_sensitive
        self._compiled_patterns = []
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile patterns into regex for efficient matching."""
        self._compiled_patterns = []
        
        if not self.patterns:
            return
        
        for pattern in self.patterns:
            try:
                # Try to compile as regex first
                flags = 0 if self.case_sensitive else re.IGNORECASE
                compiled = re.compile(pattern, flags)
                self._compiled_patterns.append(("regex", compiled))
            except re.error as e:
                # If it's not valid regex, treat it as substring match
                try:
                    flags = 0 if self.case_sensitive else re.IGNORECASE
                    # Escape the pattern for literal matching, then compile
                    escaped = re.escape(pattern)
                    compiled = re.compile(escaped, flags)
                    self._compiled_patterns.append(("substring", compiled))
                except re.error as e2:
                    raise ValueError(f"Invalid redaction pattern '{pattern}': {e2}")
    
    def should_redact(self, key: str) -> bool:
        """Determine if a key should be redacted.
        
        Args:
            key: The attribute key to check
            
        Returns:
            True if key matches any redaction pattern
        """
        if not self._compiled_patterns:
            return False
        
        for pattern_type, compiled_pattern in self._compiled_patterns:
            if pattern_type == "regex":
                # For regex patterns, try to match against the key
                if compiled_pattern.search(key):
                    return True
            else:
                # For substring patterns, check if pattern is in key
                if compiled_pattern.search(key):
                    return True
        
        return False
    
    def redact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive data in a dictionary.
        
        Args:
            data: Dictionary to redact (usually span attributes or event attributes)
            
        Returns:
            New dictionary with redacted values
        """
        if not data or not self._compiled_patterns:
            return data.copy() if isinstance(data, dict) else data
        
        return self._redact_dict(data)
    
    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact dictionary values."""
        result = {}
        
        for key, value in data.items():
            if self.should_redact(key):
                # Redact this key's value
                result[key] = self._apply_redaction(value)
            else:
                # Recursively process nested dicts
                if isinstance(value, dict):
                    result[key] = self._redact_dict(value)
                elif isinstance(value, list):
                    result[key] = self._redact_list(value, key)
                else:
                    result[key] = value
        
        return result
    
    def _redact_list(self, items: List[Any], key: str) -> List[Any]:
        """Redact items in a list if the key matches."""
        if self.should_redact(key):
            # If the key itself matches, redact all items
            return [self._apply_redaction(item) for item in items]
        
        # Otherwise, process items individually
        result = []
        for item in items:
            if isinstance(item, dict):
                result.append(self._redact_dict(item))
            elif isinstance(item, list):
                result.append(self._redact_list(item, key))
            else:
                result.append(item)
        
        return result
    
    def _apply_redaction(self, value: Any) -> Any:
        """Apply redaction to a value."""
        if value is None:
            return None
        
        if isinstance(value, str):
            return self.redaction_value
        
        if isinstance(value, (int, float, bool)):
            # Don't redact non-string types
            return value
        
        if isinstance(value, list):
            # Redact all items in list
            return [self._apply_redaction(item) for item in value]
        
        if isinstance(value, dict):
            # Redact nested dict
            return self._redact_dict(value)
        
        # For unknown types, convert to string and redact
        return self.redaction_value
