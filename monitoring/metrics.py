"""
Prometheus Metrics Collection
Provides monitoring metrics for all microservices
"""

import os
import time
from prometheus_client import (
    Counter, Histogram, Gauge, Info,
    generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST
)
from flask import Response
import logging

logger = logging.getLogger(__name__)


class MetricsManager:
    """Manages Prometheus metrics collection"""

    def __init__(self, service_name):
        """
        Initialize metrics manager

        Args:
            service_name: Name of the microservice
        """
        self.service_name = service_name
        self.registry = CollectorRegistry()
        self._setup_metrics()

    def _setup_metrics(self):
        """Setup Prometheus metrics"""

        # Service info
        self.service_info = Info(
            'service_info',
            'Service information',
            registry=self.registry
        )
        self.service_info.info({
            'service_name': self.service_name,
            'version': os.getenv('SERVICE_VERSION', '1.0.0'),
            'environment': os.getenv('ENVIRONMENT', 'development')
        })

        # Request metrics
        self.request_count = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )

        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )

        self.request_size = Histogram(
            'http_request_size_bytes',
            'HTTP request size in bytes',
            ['method', 'endpoint'],
            registry=self.registry
        )

        self.response_size = Histogram(
            'http_response_size_bytes',
            'HTTP response size in bytes',
            ['method', 'endpoint'],
            registry=self.registry
        )

        # Agent-specific metrics
        self.agent_calls = Counter(
            'agent_calls_total',
            'Total calls to other agents',
            ['source_agent', 'target_agent', 'endpoint', 'status'],
            registry=self.registry
        )

        self.agent_call_duration = Histogram(
            'agent_call_duration_seconds',
            'Agent-to-agent call duration',
            ['source_agent', 'target_agent', 'endpoint'],
            registry=self.registry
        )

        # Business metrics
        self.recommendations_generated = Counter(
            'recommendations_generated_total',
            'Total product recommendations generated',
            ['user_tier'],
            registry=self.registry
        )

        self.inventory_checks = Counter(
            'inventory_checks_total',
            'Total inventory checks',
            ['product_category', 'stock_status'],
            registry=self.registry
        )

        self.transactions_initiated = Counter(
            'transactions_initiated_total',
            'Total payment transactions initiated',
            ['currency'],
            registry=self.registry
        )

        self.transactions_completed = Counter(
            'transactions_completed_total',
            'Total successful transactions',
            ['currency', 'payment_method'],
            registry=self.registry
        )

        self.reservations_made = Counter(
            'reservations_made_total',
            'Total store reservations',
            ['store_id', 'city'],
            registry=self.registry
        )

        self.orders_tracked = Counter(
            'orders_tracked_total',
            'Total order status queries',
            ['order_status'],
            registry=self.registry
        )

        # Database metrics
        self.db_operations = Counter(
            'database_operations_total',
            'Total database operations',
            ['collection', 'operation', 'status'],
            registry=self.registry
        )

        self.db_operation_duration = Histogram(
            'database_operation_duration_seconds',
            'Database operation duration',
            ['collection', 'operation'],
            registry=self.registry
        )

        # Active connections/sessions
        self.active_sessions = Gauge(
            'active_sessions',
            'Number of active user sessions',
            registry=self.registry
        )

        self.cache_hit_rate = Gauge(
            'cache_hit_rate',
            'Cache hit rate percentage',
            ['cache_type'],
            registry=self.registry
        )

        # Error metrics
        self.errors_total = Counter(
            'errors_total',
            'Total errors',
            ['error_type', 'severity'],
            registry=self.registry
        )

        logger.info(f"Metrics initialized for {self.service_name}")

    def record_request(self, method, endpoint, status_code, duration, request_size=0, response_size=0):
        """Record HTTP request metrics"""
        self.request_count.labels(
            method=method,
            endpoint=endpoint,
            status=status_code
        ).inc()

        self.request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

        if request_size > 0:
            self.request_size.labels(
                method=method,
                endpoint=endpoint
            ).observe(request_size)

        if response_size > 0:
            self.response_size.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_size)

    def record_agent_call(self, source_agent, target_agent, endpoint, status, duration):
        """Record agent-to-agent call metrics"""
        self.agent_calls.labels(
            source_agent=source_agent,
            target_agent=target_agent,
            endpoint=endpoint,
            status=status
        ).inc()

        self.agent_call_duration.labels(
            source_agent=source_agent,
            target_agent=target_agent,
            endpoint=endpoint
        ).observe(duration)

    def record_db_operation(self, collection, operation, status, duration):
        """Record database operation metrics"""
        self.db_operations.labels(
            collection=collection,
            operation=operation,
            status=status
        ).inc()

        self.db_operation_duration.labels(
            collection=collection,
            operation=operation
        ).observe(duration)

    def record_error(self, error_type, severity="error"):
        """Record error occurrence"""
        self.errors_total.labels(
            error_type=error_type,
            severity=severity
        ).inc()

    def get_metrics(self):
        """Get current metrics for Prometheus scraping"""
        return generate_latest(self.registry)

    def create_metrics_endpoint(self, app):
        """
        Create /metrics endpoint for Flask app

        Args:
            app: Flask application instance
        """
        @app.route('/metrics')
        def metrics():
            return Response(
                self.get_metrics(),
                mimetype=CONTENT_TYPE_LATEST
            )
        logger.info(f"Metrics endpoint created at /metrics for {self.service_name}")


def timed_operation(metrics_manager, operation_name):
    """
    Decorator to time operations and record metrics

    Usage:
        @timed_operation(metrics, "get_recommendations")
        def get_recommendations():
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                # Custom metric recording can be added here
                return result
            except Exception as e:
                metrics_manager.record_error(type(e).__name__)
                raise
        return wrapper
    return decorator
