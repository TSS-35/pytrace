import os
from pytrace.config import Config

def test_config_default_values():
    config = Config()
    assert config.enabled is True
    assert config.service_name == "unnamed-python-service"

def test_config_env_override():
    os.environ["PYTRACE_ENABLED"] = "false"
    os.environ["PYTRACE_SERVICE_NAME"] = "my-test-app"
    
    config = Config()
    
    assert config.enabled is False
    assert config.service_name == "my-test-app"
    
    # Cleanup
    del os.environ["PYTRACE_ENABLED"]
    del os.environ["PYTRACE_SERVICE_NAME"]