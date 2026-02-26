import os
from typing import List, Optional

class Config:
    def __init__(self, sampler=None, redactor=None):
        # Basic Settings
        self.enabled: bool = os.getenv("PYTRACE_ENABLED", "true").lower() == "true"
        self.service_name: str = os.getenv("PYTRACE_SERVICE_NAME", "unnamed-python-service")
        
        # Sampling Configuration
        if sampler is None:
            from pytrace.sampler import NoOpSampler
            sampler = NoOpSampler()
        self.sampler = sampler
        
        # Redaction Configuration
        if redactor is None:
            from pytrace.redactor import Redactor
            redactor = Redactor(patterns=None)  # No-op redactor
        self.redactor = redactor
        
        # Performance & Noise Control
        self.exclude_modules: List[str] = [
            "pytrace",    # Don't trace the tracing library itself
            "importlib",  # Internal module loading
            "linecache",  # Traceback formatting
            "pytest",     # Testing framework internals
            "_pytest",
            "unittest",
            "threading"
        ]

    def should_trace(self, module_name: str) -> bool:
        """Helper to check if a module should be traced based on exclusions."""
        if not self.enabled:
            return False
            
        if not module_name:
            return True
            
        return not any(excluded in module_name for excluded in self.exclude_modules)