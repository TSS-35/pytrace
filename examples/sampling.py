"""Example: Using sampling strategies in pytrace."""
from pytrace.config import Config
from pytrace.tracer import Tracer
from pytrace.sampler import (
    ProbabilitySampler,
    RateLimitSampler,
    TraceIdSampler,
    AlwaysSampler,
    NoOpSampler
)
from collector.memory import MemoryCollector


# Example 1: Debug Mode - Sample Everything
print("=== Example 1: Debug Mode (No Sampling) ===")
config = Config(sampler=AlwaysSampler())
collector = MemoryCollector()
tracer = Tracer(config=config, collector=collector)

for i in range(10):
    with tracer.start_span(f"request_{i}"):
        pass

print(f"Created {len(collector.spans)} spans (sampled all)")
print()


# Example 2: Development - 50% Probability Sampling
print("=== Example 2: Development (50% Probability Sampling) ===")
config = Config(sampler=ProbabilitySampler(0.5))
collector = MemoryCollector()
tracer = Tracer(config=config, collector=collector)

for i in range(100):
    with tracer.start_span(f"operation_{i}"):
        pass

print(f"Created {len(collector.spans)} spans out of 100 (roughly 50%)")
print()


# Example 3: Production - 1% Probability Sampling (Low Volume)
print("=== Example 3: Production (1% Probability Sampling) ===")
config = Config(sampler=ProbabilitySampler(0.01))
collector = MemoryCollector()
tracer = Tracer(config=config, collector=collector)

for i in range(1000):
    with tracer.start_span(f"api_call_{i}"):
        pass

print(f"Created {len(collector.spans)} spans out of 1000 (roughly 1%)")
print()


# Example 4: Rate Limiting - Max 50 Spans/Second
print("=== Example 4: Rate Limiting (50 spans/sec max) ===")
config = Config(sampler=RateLimitSampler(50))
collector = MemoryCollector()
tracer = Tracer(config=config, collector=collector)

# Try to create 100 spans immediately
for i in range(100):
    with tracer.start_span(f"db_query_{i}"):
        pass

print(f"Created {len(collector.spans)} spans out of 100 (capped at 50/sec)")
print()


# Example 5: Trace-Level Sampling - Keep Full Traces
print("=== Example 5: Trace-Level Sampling (50% of traces) ===")
config = Config(sampler=TraceIdSampler(0.5))
collector = MemoryCollector()
tracer = Tracer(config=config, collector=collector)

# Create 10 traces, each with 3 spans
for trace_num in range(10):
    trace_id = f"trace-{trace_num}"
    with tracer.start_span("parent", trace_id=trace_id):
        with tracer.start_span("child_1"):
            pass
        with tracer.start_span("child_2"):
            pass

print(f"Created {len(collector.spans)} spans from ~5 sampled traces (all spans in trace preserved)")

# Verify trace integrity - each sampled trace has all its spans
trace_ids = {span.trace_id for span in collector.spans}
for trace_id in trace_ids:
    trace_spans = [s for s in collector.spans if s.trace_id == trace_id]
    print(f"  {trace_id}: {len(trace_spans)} spans")
print()


# Example 6: Configuration from Environment
print("=== Example 6: Practical Configuration ===")
# In production code, you might configure like this:
config = Config(sampler=ProbabilitySampler(0.01))  # 1% sampling for prod
print("Configuration: Probability-based sampling at 1%")
print(f"Sampler type: {config.sampler.__class__.__name__}")
print(f"Always samples: {config.sampler.should_sample()}")
