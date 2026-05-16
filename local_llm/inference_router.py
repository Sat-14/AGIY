"""
Intelligent LLM Inference Router
Routes requests between cloud (Gemini Pro) and edge (4-bit local) models
with graceful failover, latency-based routing, and circuit breaker patterns.
"""

import os
import time
import logging
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)


class RouterStrategy(Enum):
    CLOUD_FIRST = "cloud_first"       # Try Gemini, fallback to edge
    EDGE_FIRST = "edge_first"         # Try local 4-bit, fallback to cloud
    LATENCY_BASED = "latency_based"   # Route based on measured latency
    COST_OPTIMIZED = "cost_optimized" # Minimize API costs, prefer edge


class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failures exceeded threshold, skip provider
    HALF_OPEN = "half_open" # Testing if provider recovered


@dataclass
class ProviderHealth:
    """Tracks health metrics for a model provider"""
    failures: int = 0
    successes: int = 0
    total_requests: int = 0
    total_latency_ms: float = 0.0
    last_failure_time: float = 0.0
    circuit_state: CircuitState = CircuitState.CLOSED
    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds before retrying OPEN circuit


@dataclass
class RouteDecision:
    """Result of a routing decision"""
    provider: str
    response: str
    latency_ms: float
    fallback_used: bool = False
    error: Optional[str] = None


class InferenceRouter:
    """
    Intelligent router that directs LLM inference requests between
    cloud (Gemini Pro) and edge (4-bit quantized local models) with:
    - Circuit breaker pattern for fault tolerance
    - Latency-aware routing
    - Graceful degradation from cloud to edge
    - Request-level metrics collection
    """

    def __init__(
        self,
        agent_name: str,
        strategy: RouterStrategy = RouterStrategy.CLOUD_FIRST,
        gemini_model: str = "models/gemini-pro-latest",
        edge_model_config: Optional[Dict] = None,
    ):
        self.agent_name = agent_name
        self.strategy = strategy
        self.gemini_model = gemini_model
        self.edge_model_config = edge_model_config
        self._lock = Lock()

        # Provider health tracking
        self.providers: Dict[str, ProviderHealth] = {
            "gemini": ProviderHealth(failure_threshold=3, recovery_timeout=60.0),
            "edge": ProviderHealth(failure_threshold=5, recovery_timeout=30.0),
        }

        # Lazy-loaded clients
        self._gemini_client = None
        self._edge_manager = None

        logger.info(
            f"InferenceRouter initialized | agent={agent_name} "
            f"strategy={strategy.value}"
        )

    @property
    def gemini_client(self):
        """Lazy-load Gemini client"""
        if self._gemini_client is None:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self._gemini_client = ChatGoogleGenerativeAI(
                    model=self.gemini_model,
                    temperature=0.3,
                    google_api_key=os.getenv("GOOGLE_API_KEY"),
                )
                logger.info("Gemini Pro client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self._record_failure("gemini")
        return self._gemini_client

    @property
    def edge_manager(self):
        """Lazy-load edge LLM manager (4-bit quantized)"""
        if self._edge_manager is None:
            try:
                from local_llm.llm_manager import create_llm_manager
                self._edge_manager = create_llm_manager(
                    self.agent_name, use_ollama=True
                )
                logger.info(f"Edge 4-bit model loaded for {self.agent_name}")
            except Exception:
                try:
                    from local_llm.llm_manager import create_llm_manager
                    self._edge_manager = create_llm_manager(
                        self.agent_name, use_ollama=False
                    )
                    logger.info(f"Edge HuggingFace model loaded for {self.agent_name}")
                except Exception as e:
                    logger.error(f"Failed to initialize edge model: {e}")
                    self._record_failure("edge")
        return self._edge_manager

    def route(self, prompt: str, context: Optional[Dict] = None) -> RouteDecision:
        """
        Route inference request to optimal provider based on strategy.
        Implements graceful failover between cloud and edge models.
        """
        if self.strategy == RouterStrategy.CLOUD_FIRST:
            return self._cloud_first_route(prompt, context)
        elif self.strategy == RouterStrategy.EDGE_FIRST:
            return self._edge_first_route(prompt, context)
        elif self.strategy == RouterStrategy.LATENCY_BASED:
            return self._latency_based_route(prompt, context)
        elif self.strategy == RouterStrategy.COST_OPTIMIZED:
            return self._edge_first_route(prompt, context)
        else:
            return self._cloud_first_route(prompt, context)

    def _cloud_first_route(self, prompt: str, context: Optional[Dict]) -> RouteDecision:
        """Try Gemini Pro first, gracefully failover to 4-bit edge model"""

        # Attempt cloud (Gemini Pro)
        if self._is_provider_available("gemini"):
            result = self._invoke_gemini(prompt)
            if result is not None:
                return result

        # Failover to edge (4-bit local model)
        logger.warning(
            f"[{self.agent_name}] Gemini unavailable, failing over to edge model"
        )
        result = self._invoke_edge(prompt, context)
        if result is not None:
            result.fallback_used = True
            return result

        # Both providers failed
        return RouteDecision(
            provider="none",
            response="Service temporarily unavailable. Please retry.",
            latency_ms=0,
            fallback_used=True,
            error="All inference providers unavailable",
        )

    def _edge_first_route(self, prompt: str, context: Optional[Dict]) -> RouteDecision:
        """Try edge model first, failover to Gemini for complex queries"""

        if self._is_provider_available("edge"):
            result = self._invoke_edge(prompt, context)
            if result is not None:
                return result

        # Failover to cloud
        logger.warning(
            f"[{self.agent_name}] Edge model unavailable, failing over to Gemini"
        )
        result = self._invoke_gemini(prompt)
        if result is not None:
            result.fallback_used = True
            return result

        return RouteDecision(
            provider="none",
            response="Service temporarily unavailable. Please retry.",
            latency_ms=0,
            fallback_used=True,
            error="All inference providers unavailable",
        )

    def _latency_based_route(self, prompt: str, context: Optional[Dict]) -> RouteDecision:
        """Route to provider with lower average latency"""
        gemini_health = self.providers["gemini"]
        edge_health = self.providers["edge"]

        gemini_avg = (
            gemini_health.total_latency_ms / max(gemini_health.total_requests, 1)
        )
        edge_avg = (
            edge_health.total_latency_ms / max(edge_health.total_requests, 1)
        )

        if edge_avg <= gemini_avg and self._is_provider_available("edge"):
            return self._edge_first_route(prompt, context)
        else:
            return self._cloud_first_route(prompt, context)

    def _invoke_gemini(self, prompt: str) -> Optional[RouteDecision]:
        """Invoke Gemini Pro with latency tracking"""
        try:
            start = time.time()
            client = self.gemini_client
            if client is None:
                return None

            response = client.invoke(prompt)
            latency_ms = (time.time() - start) * 1000

            self._record_success("gemini", latency_ms)
            return RouteDecision(
                provider="gemini_pro",
                response=response.content,
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.error(f"Gemini invocation failed: {e}")
            self._record_failure("gemini")
            return None

    def _invoke_edge(self, prompt: str, context: Optional[Dict]) -> Optional[RouteDecision]:
        """Invoke 4-bit quantized edge model with latency tracking"""
        try:
            start = time.time()
            manager = self.edge_manager
            if manager is None:
                return None

            response = manager.generate(prompt)
            latency_ms = (time.time() - start) * 1000

            self._record_success("edge", latency_ms)
            return RouteDecision(
                provider=f"edge_4bit_{self.agent_name}",
                response=response,
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.error(f"Edge model invocation failed: {e}")
            self._record_failure("edge")
            return None

    def _is_provider_available(self, provider: str) -> bool:
        """Check if provider is available (circuit breaker logic)"""
        with self._lock:
            health = self.providers[provider]

            if health.circuit_state == CircuitState.CLOSED:
                return True

            if health.circuit_state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed
                elapsed = time.time() - health.last_failure_time
                if elapsed >= health.recovery_timeout:
                    health.circuit_state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit half-open for {provider}, testing...")
                    return True
                return False

            # HALF_OPEN: allow one request through
            return True

    def _record_success(self, provider: str, latency_ms: float):
        """Record successful invocation"""
        with self._lock:
            health = self.providers[provider]
            health.successes += 1
            health.total_requests += 1
            health.total_latency_ms += latency_ms

            if health.circuit_state == CircuitState.HALF_OPEN:
                health.circuit_state = CircuitState.CLOSED
                health.failures = 0
                logger.info(f"Circuit closed for {provider} (recovered)")

    def _record_failure(self, provider: str):
        """Record failed invocation, potentially open circuit"""
        with self._lock:
            health = self.providers[provider]
            health.failures += 1
            health.total_requests += 1
            health.last_failure_time = time.time()

            if health.failures >= health.failure_threshold:
                health.circuit_state = CircuitState.OPEN
                logger.warning(
                    f"Circuit OPEN for {provider} "
                    f"(failures={health.failures}/{health.failure_threshold})"
                )

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status of all providers"""
        status = {}
        for name, health in self.providers.items():
            avg_latency = (
                health.total_latency_ms / max(health.total_requests, 1)
            )
            status[name] = {
                "circuit_state": health.circuit_state.value,
                "total_requests": health.total_requests,
                "failures": health.failures,
                "successes": health.successes,
                "avg_latency_ms": round(avg_latency, 2),
                "success_rate": round(
                    health.successes / max(health.total_requests, 1) * 100, 1
                ),
            }
        return {
            "agent": self.agent_name,
            "strategy": self.strategy.value,
            "providers": status,
        }


def create_inference_router(
    agent_name: str,
    strategy: str = "cloud_first",
) -> InferenceRouter:
    """Factory function to create an inference router for an agent"""
    strategy_map = {
        "cloud_first": RouterStrategy.CLOUD_FIRST,
        "edge_first": RouterStrategy.EDGE_FIRST,
        "latency_based": RouterStrategy.LATENCY_BASED,
        "cost_optimized": RouterStrategy.COST_OPTIMIZED,
    }
    return InferenceRouter(
        agent_name=agent_name,
        strategy=strategy_map.get(strategy, RouterStrategy.CLOUD_FIRST),
    )
