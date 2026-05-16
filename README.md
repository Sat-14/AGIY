# Multi-Agent Sales System (AGIY)

Distributed multi-agent AI system for fashion retail, built with LangChain-orchestrated LLM meshes, edge-optimized 4-bit inference, and production-grade Kubernetes deployment with full observability.

## Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                          USER (CLI / API)                              │
└──────────────────────────────┬────────────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│              SALES AGENT (LangChain + Gemini Pro)                      │
│         Orchestrator │ Memory │ Tool Selection │ Routing               │
└───┬─────���───┬──────────┬──────────┬──────────┬───────────────────────┘
    │         │          │          │          │
    │ REST    │ REST     │ REST     │ REST     │ REST
    ▼         ▼          ▼          ▼          ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
│Recom.  ││Inven.  ││Fulfill.││Payment │���Post-   │
│Agent   ││Agent   ││Agent   ││Agent   ││Purchase│
│:5002   ││:5003   ││:5001   ││:5005   ││:5004   │
└───┬────┘└───┬────┘└────────┘└────────┘└────────┘
    │         │
    ▼         ▼
┌──────────────────────────────────────┐
│  Inference Router (Circuit Breaker)  │
│  Gemini Pro ──failover─��► 4-bit Edge │
└──────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│  Edge Models (4-bit Quantized)       │
│  TinyLlama │ StableLM │ Qwen │ Phi-2│
│  QLoRA Fine-tuning + Hot Reload      │
└──────────────────────────────────────┘
```

---

## Key Technical Highlights

### 1. Distributed Multi-Agent LLM Mesh (LangChain + 4-bit Edge Models)

Engineered multi-agent architecture with LangChain orchestrating 6 specialized agents communicating via REST, each backed by edge-optimized 4-bit quantized models.

```python
# main.py - LangChain Agent Mesh Orchestrator

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from tools import all_tools  # 6 agent tools via REST

llm = ChatGoogleGenerativeAI(model="models/gemini-pro-latest", temperature=0)

agent = create_tool_calling_agent(llm, all_tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=all_tools,   # Recommendation, Inventory, Fulfillment, Payment, etc.
    verbose=True,
    memory=memory,
)
```

```python
# local_llm/model_config.py - 4-bit Edge Model Configurations

RTX_3060_CONFIGS = {
    "recommendation": LLMConfig(
        model_name="google/gemma-2b-it",
        model_type=ModelType.GEMMA_2B,
        quantization="4bit",
        max_tokens=384,
        temperature=0.7,
        gpu_memory_fraction=0.4,  # 2.4GB VRAM
    ),
    "inventory": LLMConfig(
        model_name="microsoft/phi-3-mini-4k-instruct",
        model_type=ModelType.PHI_3_MINI,
        quantization="4bit",
        max_tokens=256,
        temperature=0.3,
        gpu_memory_fraction=0.4,
    ),
}
```

---

### 2. QLoRA Fine-Tuning Pipeline (Dynamic LoRA Updates in 6GB VRAM)

Architected QLoRA training pipeline with NF4 quantization, paged AdamW 8-bit optimizer, and gradient checkpointing — enabling continuous model improvement within 6GB VRAM constraints.

```
  User Feedback ──► Feedback Store (JSONL)
                         │
              (threshold: 50 samples)
                         ▼
  ┌─────────────────────────────────────────┐
  │  QLoRA Training Pipeline                │
  │  Base Model (4-bit NF4) + LoRA(r=4)    │
  │  Batch=1 │ GradAccum=8 │ fp16          │
  │  paged_adamw_8bit │ grad_checkpoint    │
  └────────────────────┬────────────────────┘
                       ▼
  LoRA Adapters (~30MB) ──��� Hot Reload (zero downtime)
```

```python
# local_llm/training_pipeline.py

def setup_qlora_training(self):
    """QLoRA setup for 6GB VRAM (RTX 3060 / M1 8GB)"""
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4"
    )

    model = AutoModelForCausalLM.from_pretrained(
        self.base_model,
        quantization_config=bnb_config,
        device_map="auto",
    )
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=4,                # Low rank for memory efficiency
        lora_alpha=8,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"]
    )
    model = get_peft_model(model, lora_config)

    training_args = TrainingArguments(
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        fp16=True,
        optim="paged_adamw_8bit",
        gradient_checkpointing=True,
    )
    return model, tokenizer, training_args
```

```python
# local_llm/llm_manager.py - Dynamic LoRA Hot Reload

# Load LoRA adapters if they exist (hot-swappable)
if os.path.exists(self.lora_path):
    self.model = PeftModel.from_pretrained(
        self.model,
        self.lora_path,
        is_trainable=False
    )
```

---

### 3. Intelligent LLM Inference Router (Gemini Pro → 4-bit Edge Failover)

Created inference router with circuit breaker pattern, latency-aware routing, and graceful degradation from cloud Gemini Pro to local 4-bit quantized edge models.

```
  Request ──► InferenceRouter
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
  ┌─────────────┐     ┌─────────────┐
  │ Gemini Pro  │     │ Edge 4-bit  │
  │ (Cloud)     │     │ (Local)     │
  └──────┬──────┘     └──────┬──────┘
         │                   │
         ▼                   ▼
  Circuit Breaker    Circuit Breaker
  (3 failures=OPEN)  (5 failures=OPEN)
         │                   │
         └──��──────┬─────────┘
                   ▼
           RouteDecision {provider, response, latency_ms}
```

```python
# local_llm/inference_router.py

class InferenceRouter:
    """Routes between cloud (Gemini) and edge (4-bit) with circuit breaker"""

    def __init__(self, agent_name, strategy=RouterStrategy.CLOUD_FIRST):
        self.providers = {
            "gemini": ProviderHealth(failure_threshold=3, recovery_timeout=60.0),
            "edge": ProviderHealth(failure_threshold=5, recovery_timeout=30.0),
        }

    def _cloud_first_route(self, prompt, context):
        """Try Gemini Pro first, gracefully failover to 4-bit edge model"""
        if self._is_provider_available("gemini"):
            result = self._invoke_gemini(prompt)
            if result is not None:
                return result

        # Failover to edge (4-bit local model)
        logger.warning(f"Gemini unavailable, failing over to edge model")
        result = self._invoke_edge(prompt, context)
        if result is not None:
            result.fallback_used = True
            return result

    def _is_provider_available(self, provider):
        """Circuit breaker: CLOSED→OPEN after N failures, HALF_OPEN after timeout"""
        health = self.providers[provider]
        if health.circuit_state == CircuitState.OPEN:
            elapsed = time.time() - health.last_failure_time
            if elapsed >= health.recovery_timeout:
                health.circuit_state = CircuitState.HALF_OPEN
                return True
            return False
        return True
```

---

### 4. OpenTelemetry Distributed Tracing + Prometheus Metrics

Built full observability stack with OpenTelemetry spans propagating across all microservices, Prometheus counters/histograms for agent-to-agent calls, and Grafana dashboards.

```
  Agent Request ──► OpenTelemetry Span
                         ���
      ┌──────────────────┼──────────────────┐
      ▼                  ▼                  ▼
  Sales Agent       Recom. Agent       Invent. Agent
  (trace_id=X)      (trace_id=X)       (trace_id=X)
      │                  │                  │
      ▼                  ▼                  ▼
  ┌──────────┐    ┌──────────┐    ┌──────────┐
  │ Jaeger   │    │Prometheus│    │ Grafana  │
  │ :16686   │    │ :9090    │    │ :3000    │
  └──────────┘    └──────────┘    └──────────┘
```

```python
# monitoring/tracing.py

class TracingManager:
    """OpenTelemetry distributed tracing across agent mesh"""

    def _setup_tracing(self):
        resource = Resource(attributes={
            SERVICE_NAME: self.service_name,
            SERVICE_VERSION: self.service_version,
        })
        self.tracer_provider = TracerProvider(resource=resource)

        if exporter_type == "jaeger":
            jaeger_exporter = JaegerExporter(
                agent_host_name=os.getenv("JAEGER_HOST", "localhost"),
                agent_port=int(os.getenv("JAEGER_PORT", 6831)),
            )
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(jaeger_exporter)
            )
        elif exporter_type == "otlp":
            otlp_exporter = OTLPSpanExporter(
                endpoint=os.getenv("OTLP_ENDPOINT", "http://localhost:4317"),
            )
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )
```

```python
# monitoring/metrics.py

class MetricsManager:
    """Prometheus metrics for agent mesh observability"""

    def _setup_metrics(self):
        self.request_count = Counter(
            'http_requests_total', 'Total HTTP requests',
            ['method', 'endpoint', 'status'], registry=self.registry
        )
        self.request_duration = Histogram(
            'http_request_duration_seconds', 'Request duration',
            ['method', 'endpoint'], registry=self.registry
        )
        self.agent_calls = Counter(
            'agent_calls_total', 'Inter-agent calls',
            ['source_agent', 'target_agent', 'status'], registry=self.registry
        )
        self.agent_call_duration = Histogram(
            'agent_call_duration_seconds', 'Agent-to-agent latency',
            ['source_agent', 'target_agent'], registry=self.registry
        )
        self.recommendations_generated = Counter(
            'recommendations_generated_total', 'Recommendations served',
            ['user_tier'], registry=self.registry
        )
```

---

### 5. Kubernetes with Horizontal Pod Autoscaling for LLM Traffic

Deployed multi-agent mesh on Kubernetes with per-agent HPA scaling on CPU, memory, and custom metrics (inference queue depth), with stabilization windows tuned for LLM cold-start latency.

```
┌─────────────────── EKS Cluster ───────────────────────┐
│                                                        │
│  ┌─── Namespace: multi-agent-sales ────────────────┐  │
│  │                                                  │  │
│  │  Sales Agent (2-10 pods)        HPA: CPU 70%    │  │
│  │  Recommendation Agent (2-8)     HPA: queue < 5  │  │
│  │  Inventory Agent (2-6)          HPA: CPU 70%    │  │
│  │  Fulfillment Agent (2-4)        HPA: CPU 70%    │  │
│  │  Payment Agent (2-4)            HPA: CPU 70%    │  │
│  │                                                  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  Ingress (nginx) ──► Service Mesh ──► Pod Routing      │
│  Prometheus ──► Custom Metrics API ──► HPA Decisions   │
└────────────────────────────────────────────────────────┘
```

```yaml
# k8s/hpa.yaml

apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: recommendation-agent-hpa
  namespace: multi-agent-sales
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: recommendation-agent
  minReplicas: 2
  maxReplicas: 8
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 65
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 75
    - type: Pods
      pods:
        metric:
          name: llm_inference_queue_depth
        target:
          type: AverageValue
          averageValue: "5"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Pods
          value: 1
          periodSeconds: 90
    scaleDown:
      stabilizationWindowSeconds: 600   # Slow scale-down (LLM model loading is expensive)
      policies:
        - type: Pods
          value: 1
          periodSeconds: 180
```

```yaml
# k8s/agent-deployment.yaml (excerpt)

spec:
  containers:
    - name: recommendation-agent
      image: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/recommendation-agent:latest
      resources:
        requests:
          cpu: "250m"
          memory: "2Gi"
          nvidia.com/gpu: "0"
        limits:
          cpu: "1000m"
          memory: "6Gi"
          nvidia.com/gpu: "1"
      livenessProbe:
        httpGet:
          path: /health
          port: 5002
        initialDelaySeconds: 60    # Allow model loading time
      readinessProbe:
        httpGet:
          path: /health
          port: 5002
        initialDelaySeconds: 30
```

---

### 6. AWS CI/CD Pipeline (GitHub Actions + ECR)

Engineered automated CI/CD with matrix builds for all agent containers, pushed to ECR, and deployed to EKS with rolling updates and health verification.

```
  git push main
       │
       ▼
  ┌─────────────────────────────────────────────┐
  │  GitHub Actions Pipeline                     │
  │                                              │
  │  1. Test ���─► Lint + Unit Tests               │
  │       │                                      │
  │       ▼                                      │
  │  2. Build (Matrix: 5 agents in parallel)     │
  │       │                                      │
  │       ▼                                      │
  │  3. Push to ECR ──► tag: sha + latest        │
  │       │                                      │
  │       ▼                                      │
  │  4. Deploy to EKS                            │
  │       ├── kubectl apply (deployments)        │
  │       ├── kubectl apply (HPA)                │
  │       └── rollout status (health check)      │
  └─────────────────────────────────────────────┘
```

```yaml
# .github/workflows/deploy.yml

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        agent:
          - name: sales-agent
          - name: recommendation-agent
          - name: inventory-agent
          - name: fulfillment-agent
          - name: payment-agent
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-south-1

      - name: Login to Amazon ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, and push to ECR
        run: |
          docker build -t $ECR_REGISTRY/${{ matrix.agent.name }}:${{ github.sha }} .
          docker push $ECR_REGISTRY/${{ matrix.agent.name }}:${{ github.sha }}
          docker push $ECR_REGISTRY/${{ matrix.agent.name }}:latest

  deploy:
    needs: build-and-push
    steps:
      - name: Deploy to EKS
        run: |
          aws eks update-kubeconfig --name multi-agent-sales-cluster
          kubectl apply -f k8s/services.yaml
          envsubst < k8s/agent-deployment.yaml | kubectl apply -f -
          kubectl apply -f k8s/hpa.yaml

      - name: Verify rollout
        run: |
          kubectl rollout status deployment/sales-agent -n multi-agent-sales
          kubectl rollout status deployment/recommendation-agent -n multi-agent-sales
```

---

## Quick Start

```bash
# Local development
pip install -r requirements.txt
echo "GOOGLE_API_KEY=your_key" > .env

# Start agents
python recommendation-agent/agent.py &    # :5002
python inventory-agent/agent.py &          # :5003
python fulfillment-agent/agent.py &        # :5001
python payment-agent/agent.py &            # :5005
python post_purchase_agent/agent.py &      # :5004
python main.py                             # Sales orchestrator

# With monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d
python main_enhanced.py
```

---

## Project Structure

```
AGIY/
├── main.py / main_enhanced.py     # LangChain orchestrator (Gemini Pro)
├── tools.py                       # Agent tool definitions (REST calls)
├── local_llm/
│   ���── inference_router.py        # Cloud↔Edge routing + circuit breaker
│   ├── llm_manager.py            # 4-bit model loading + LoRA hot-reload
│   ├── training_pipeline.py      # QLoRA fine-tuning (6GB VRAM)
│   └── model_config.py           # RTX 3060 / M1 optimized configs
├── recommendation-agent/          # TinyLlama 1.1B (4-bit)
├── inventory-agent/               # StableLM 1.6B (4-bit)
├── fulfillment-agent/             # Qwen 1.8B (4-bit)
├── payment-agent/                 # StableLM 1.6B (4-bit)
├── post_purchase_agent/           # TinyLlama 1.1B (4-bit)
├── monitoring/
│   ├── tracing.py                # OpenTelemetry + Jaeger
│   ├── metrics.py                # Prometheus counters/histograms
│   └─�� logging_config.py        # Structured JSON logs
├── k8s/
│   ├── agent-deployment.yaml     # Deployments with GPU resources
│   ├── hpa.yaml                  # HPA with custom LLM metrics
│   └── services.yaml            # Services + Ingress
├── .github/workflows/
│   └── deploy.yml               # CI/CD → ECR → EKS
├── Dockerfile                    # Sales agent container
├── Dockerfile.agent              # Worker agent container (parameterized)
└── docker-compose.monitoring.yml # Local observability stack
```
