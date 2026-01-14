from pytrace.tracer import Tracer
from pytrace.config import Config

# Initialize global configuration and tracer
default_config = Config()
tracer = Tracer(config=default_config)

# Export for easy access: from pytrace import tracer
__all__ = ["tracer", "default_config"]