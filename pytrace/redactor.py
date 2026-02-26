"""Span redaction for masking sensitive data (PII, credentials, etc.)."""
import re
from typing import List, Optional, Dict, Any


class Redactor:
    """Redacts sensitive data from span attributes and events.
    
    Security Notes:
    - By default (safe_mode=True), only allows literal substring patterns
    - Regex patterns can be vulnerable to ReDoS (Regular Expression Denial of Service)
    - If enable_regex=True, use only trusted, simple patterns
    - Complex regex like (a+)+b can cause catastrophic backtracking
    - Never use untrusted user input as regex patterns
    
    Performance Notes:
    - By default, creates new dictionaries during redaction (safe, defensive)
    - For high-volume tracing, set inplace=True to mutate dictionaries in-place
    - Inplace mutation is ~2-3x faster but modifies the input dictionary
    - Deeply nested structures have linear time complexity in structure depth
    """
    
    def __init__(
        self,
        patterns: Optional[List[str]] = None,
        redaction_value: str = "***REDACTED***",
        case_sensitive: bool = False,
        inplace: bool = False,
        enable_regex: bool = False
    ):
        """Initialize redactor with patterns.
        
        Args:
            patterns: List of pattern strings to match
                    If enable_regex=False: treated as literal substrings (safe)
                    If enable_regex=True: compiled as regex patterns (faster but requires trusted input)
            redaction_value: Default value to replace matched content
            case_sensitive: Whether pattern matching is case-sensitive
            inplace: If True, mutate dictionaries in-place (faster for high-volume)
                    If False (default), create new dictionaries (safer)
            enable_regex: If True, compile patterns as regex (ReDoS risk)
                         If False (default), treat patterns as literal substrings (safe)
                         
        Raises:
            ValueError: If pattern is invalid regex and enable_regex=True
        """
        self.patterns = patterns or []
        self.redaction_value = redaction_value
        self.case_sensitive = case_sensitive
        self.inplace = inplace
        self.enable_regex = enable_regex
        self._compiled_patterns = []
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile patterns into regex for efficient matching.
        
        If enable_regex=False (default, safe):
            - Patterns are escaped as literal substrings
            - No ReDoS vulnerability
            
        If enable_regex=True (risky):
            - Patterns are compiled as regex
            - Only use with trusted patterns
            - Complex patterns can cause catastrophic backtracking
        """
        self._compiled_patterns = []
        
        if not self.patterns:
            return
        
        flags = 0 if self.case_sensitive else re.IGNORECASE
        
        for pattern in self.patterns:
            try:
                if self.enable_regex:
                    # User explicitly wants regex - compile as-is
                    # This is risky with untrusted input (ReDoS vulnerability)
                    compiled = re.compile(pattern, flags)
                else:
                    # Safe mode: always escape pattern for literal matching
                    escaped = re.escape(pattern)
                    compiled = re.compile(escaped, flags)
                
                self._compiled_patterns.append(compiled)
            except re.error as e:
                raise ValueError(f"Invalid pattern '{pattern}': {e}")
    
    def should_redact(self, key: str) -> bool:
        """Determine if a key should be redacted.
        
        Args:
            key: The attribute key to check
            
        Returns:
            True if key matches any redaction pattern
        """
        if not self._compiled_patterns:
            return False
        
        for compiled_pattern in self._compiled_patterns:
            if compiled_pattern.search(key):
                return True
        
        return False
    
    def redact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive data in a dictionary.
        
        Args:
            data: Dictionary to redact (usually span attributes or event attributes)
            
        Returns:
            New dictionary with redacted values (or mutated input if inplace=True)
        """
        if not data or not self._compiled_patterns:
            return data if self.inplace else (data.copy() if isinstance(data, dict) else data)
        
        if self.inplace:
            return self._redact_dict_inplace(data)
        else:
            return self._redact_dict(data)
    
    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact dictionary values (non-mutating)."""
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
    
    def _redact_dict_inplace(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact dictionary values (mutating for performance)."""
        for key, value in list(data.items()):
            if self.should_redact(key):
                # Redact this key's value
                data[key] = self._apply_redaction(value)
            else:
                # Recursively process nested dicts
                if isinstance(value, dict):
                    self._redact_dict_inplace(value)
                elif isinstance(value, list):
                    self._redact_list_inplace(value, key)
        
        return data
    
    def _redact_list(self, items: List[Any], key: str) -> List[Any]:
        """Redact items in a list if the key matches (non-mutating)."""
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
    
    def _redact_list_inplace(self, items: List[Any], key: str) -> None:
        """Redact items in a list if the key matches (mutating for performance)."""
        if self.should_redact(key):
            # If the key itself matches, redact all items
            for i in range(len(items)):
                items[i] = self._apply_redaction(items[i])
        else:
            # Otherwise, process items individually
            for item in items:
                if isinstance(item, dict):
                    self._redact_dict_inplace(item)
                elif isinstance(item, list):
                    self._redact_list_inplace(item, key)
    
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
