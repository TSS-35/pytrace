"""Example: Using span redaction to mask sensitive data."""
from pytrace.config import Config
from pytrace.tracer import Tracer
from pytrace.redactor import Redactor
from collector.memory import MemoryCollector


print("=== Example 1: Basic Redaction ===")
# Define patterns for sensitive data
patterns = ["password", "api_key", "token"]
redactor = Redactor(patterns=patterns)
config = Config(redactor=redactor)
collector = MemoryCollector()
tracer = Tracer(config=config, collector=collector)

with tracer.start_span("user_login") as span:
    span.attributes["username"] = "alice"
    span.attributes["password"] = "super_secret_123"  # Will be redacted
    span.attributes["ip_address"] = "192.168.1.1"

collected = collector.spans[0]
print(f"Username: {collected.attributes['username']}")
print(f"Password: {collected.attributes['password']}")  # Should be redacted
print(f"IP: {collected.attributes['ip_address']}")
print()


print("=== Example 2: Custom Redaction Value ===")
redactor = Redactor(patterns=["api_key"], redaction_value="[MASKED]")
config = Config(redactor=redactor)
collector = MemoryCollector()
tracer = Tracer(config=config, collector=collector)

with tracer.start_span("api_call") as span:
    span.attributes["endpoint"] = "/api/users"
    span.attributes["api_key"] = "sk_live_1234567890"  # Custom mask

collected = collector.spans[0]
print(f"Endpoint: {collected.attributes['endpoint']}")
print(f"API Key: {collected.attributes['api_key']}")  # Custom masked value
print()


print("=== Example 3: Redacting Event Attributes ===")
patterns = ["credit_card", "cvv"]
redactor = Redactor(patterns=patterns)
config = Config(redactor=redactor)
collector = MemoryCollector()
tracer = Tracer(config=config, collector=collector)

with tracer.start_span("payment_processing") as span:
    span.attributes["amount"] = "99.99"
    
    span.add_event("card_validated", attributes={
        "credit_card": "4532-0151-1283-0366",  # Will be redacted
        "cvv": "123",  # Will be redacted
        "valid": "true"
    })

collected = collector.spans[0]
event = collected.events[0]
print(f"Amount (span attr): {collected.attributes['amount']}")
print(f"Credit Card (event): {event['attributes']['credit_card']}")  # Redacted
print(f"CVV (event): {event['attributes']['cvv']}")  # Redacted
print(f"Valid (event): {event['attributes']['valid']}")
print()


print("=== Example 4: Real-World Patterns ===")
# Common PII and sensitive fields
patterns = [
    "password",
    "api_key",
    "api_secret",
    "secret",
    "token",
    "auth",
    "ssn",
    "credit_card"
]
redactor = Redactor(patterns=patterns)
config = Config(redactor=redactor)
collector = MemoryCollector()
tracer = Tracer(config=config, collector=collector)

# Simulate a real application scenario
with tracer.start_span("user_signup") as span:
    span.attributes["email"] = "user@example.com"  # Preserved
    span.attributes["password"] = "MyP@ssw0rd"  # Redacted
    span.attributes["ssn"] = "123-45-6789"  # Redacted
    span.attributes["api_key"] = "sk_test_abc123"  # Redacted

collected = collector.spans[0]
print("Signup flow attributes:")
for key, value in collected.attributes.items():
    print(f"  {key}: {value}")
print()


print("=== Example 5: Pattern Matching ===")
# Patterns can be partial matches
redactor = Redactor(patterns=["_secret", "_token", "_key"])
config = Config(redactor=redactor)
collector = MemoryCollector()
tracer = Tracer(config=config, collector=collector)

with tracer.start_span("auth") as span:
    span.attributes["app_secret"] = "secret_value"  # Redacted
    span.attributes["refresh_token"] = "token_value"  # Redacted
    span.attributes["api_key"] = "key_value"  # Redacted
    span.attributes["username"] = "john_doe"  # NOT redacted
    span.attributes["user_secret"] = "sensitive"  # Redacted (contains _secret)

collected = collector.spans[0]
print("Pattern matching results:")
for key, value in collected.attributes.items():
    print(f"  {key}: {value}")
