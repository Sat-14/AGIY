"""
Distributed Tracing Configuration using OpenTelemetry
Provides end-to-end request tracing across all microservices
"""

import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.trace import Status, StatusCode
import logging

logger = logging.getLogger(__name__)


class TracingManager:
    """Manages OpenTelemetry distributed tracing"""

    def __init__(self, service_name, service_version="1.0.0"):
        """
        Initialize tracing for a service

        Args:
            service_name: Name of the microservice
            service_version: Version of the service
        """
        self.service_name = service_name
        self.service_version = service_version
        self.tracer_provider = None
        self.tracer = None
        self._setup_tracing()

    def _setup_tracing(self):
        """Configure OpenTelemetry tracing"""
        # Create resource with service information
        resource = Resource(attributes={
            SERVICE_NAME: self.service_name,
            SERVICE_VERSION: self.service_version,
            "environment": os.getenv("ENVIRONMENT", "development")
        })

        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)

        # Configure exporters based on environment
        exporter_type = os.getenv("TRACE_EXPORTER", "console")

        if exporter_type == "jaeger":
            # Jaeger exporter (for local development/testing)
            jaeger_exporter = JaegerExporter(
                agent_host_name=os.getenv("JAEGER_HOST", "localhost"),
                agent_port=int(os.getenv("JAEGER_PORT", 6831)),
            )
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(jaeger_exporter)
            )
            logger.info(f"Jaeger tracing enabled for {self.service_name}")

        elif exporter_type == "otlp":
            # OTLP exporter (for production with collectors like Tempo/Zipkin)
            otlp_exporter = OTLPSpanExporter(
                endpoint=os.getenv("OTLP_ENDPOINT", "http://localhost:4317"),
                insecure=True
            )
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )
            logger.info(f"OTLP tracing enabled for {self.service_name}")

        else:
            # Console exporter (development)
            console_exporter = ConsoleSpanExporter()
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(console_exporter)
            )
            logger.info(f"Console tracing enabled for {self.service_name}")

        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)

        # Get tracer
        self.tracer = trace.get_tracer(__name__)

        # Auto-instrument libraries
        RequestsInstrumentor().instrument()
        PymongoInstrumentor().instrument()

        logger.info(f"Tracing initialized for {self.service_name}")

    def instrument_flask_app(self, app):
        """
        Instrument a Flask application

        Args:
            app: Flask application instance
        """
        FlaskInstrumentor().instrument_app(app)
        logger.info(f"Flask app instrumented for {self.service_name}")

    def create_span(self, name, attributes=None):
        """
        Create a custom span

        Args:
            name: Span name
            attributes: Optional span attributes

        Returns:
            Span context manager
        """
        span = self.tracer.start_as_current_span(name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        return span

    def add_span_event(self, name, attributes=None):
        """
        Add an event to the current span

        Args:
            name: Event name
            attributes: Optional event attributes
        """
        current_span = trace.get_current_span()
        current_span.add_event(name, attributes=attributes or {})

    def record_exception(self, exception):
        """
        Record an exception in the current span

        Args:
            exception: Exception object
        """
        current_span = trace.get_current_span()
        current_span.record_exception(exception)
        current_span.set_status(Status(StatusCode.ERROR, str(exception)))

    def set_span_attribute(self, key, value):
        """Add attribute to current span"""
        current_span = trace.get_current_span()
        current_span.set_attribute(key, value)


def trace_function(func):
    """
    Decorator to trace a function

    Usage:
        @trace_function
        def my_function():
            pass
    """
    def wrapper(*args, **kwargs):
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(func.__name__):
            return func(*args, **kwargs)
    return wrapper


def trace_agent_call(agent_name, endpoint):
    """
    Decorator to trace inter-agent API calls

    Usage:
        @trace_agent_call("recommendation-agent", "/get-recommendations")
        def call_recommendation_agent():
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(f"{agent_name}.{endpoint}") as span:
                span.set_attribute("agent.name", agent_name)
                span.set_attribute("agent.endpoint", endpoint)
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        return wrapper
    return decorator
