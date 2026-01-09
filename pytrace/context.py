import contextvars

# The "source of truth" for the active span
active_span_var = contextvars.ContextVar("active_span", default=None)