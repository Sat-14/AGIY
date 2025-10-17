# Migration Guide: Standard → Enhanced Version

## Overview

The Sales Agent system now has two versions:
- **Standard Version**: Simple, minimal dependencies, works immediately
- **Enhanced Version**: Production-ready with MongoDB & monitoring

## Quick Comparison

| Feature | Standard | Enhanced |
|---------|----------|----------|
| **Conversation Memory** | In-memory (lost on restart) | MongoDB (persistent) |
| **User Profiles** | Mock data | MongoDB |
| **Inventory Data** | Mock data | MongoDB |
| **Distributed Tracing** | ❌ None | ✅ OpenTelemetry + Jaeger |
| **Metrics** | ❌ None | ✅ Prometheus + Grafana |
| **Structured Logging** | ❌ Print statements | ✅ JSON logs with trace context |
| **Dependencies** | 4 packages | 15+ packages |
| **Setup Time** | 2 minutes | 15-30 minutes |
| **Production Ready** | No | Yes |

## File Mapping

### Main Agent
- **Standard:** `main.py`
- **Enhanced:** `main_enhanced.py`

### Recommendation Agent
- **Standard:** `recommendation-agent/agent.py`
- **Enhanced:** `recommendation-agent/agent_enhanced.py`

### Inventory Agent
- **Standard:** `inventory-agent/agent.py`
- **Enhanced:** `inventory-agent/agent_enhanced.py`

### Other Agents (Fulfillment, Payment, Post-Purchase, Loyalty)
- **Standard:** `<agent-name>/agent.py` (already available)
- **Enhanced:** Not yet created (use standard version or adapt pattern)

## When to Use Each Version

### Use Standard Version If:
- ✅ Quick testing/prototyping
- ✅ Learning/understanding the system
- ✅ Minimal infrastructure available
- ✅ Don't need conversation persistence
- ✅ Local development only

### Use Enhanced Version If:
- ✅ Production deployment
- ✅ Need conversation history persistence
- ✅ Want to monitor system performance
- ✅ Need distributed tracing
- ✅ Handling real users
- ✅ Need analytics/insights

## Migration Steps

### Option 1: Quick Start (Standard Version)

```bash
# 1. Install minimal dependencies
pip install langchain langchain-google-genai python-dotenv requests flask

# 2. Configure .env
echo "GOOGLE_API_KEY=your_key_here" > .env

# 3. Run agents (open multiple terminals)
python recommendation-agent/agent.py   # Terminal 1
python inventory-agent/agent.py        # Terminal 2
python fulfillment-agent/agent.py      # Terminal 3
python payment-agent/agent.py          # Terminal 4
python post_purchase_agent/agent.py    # Terminal 5
python loyalty-agent/agent.py          # Terminal 6
python main.py                         # Terminal 7
```

### Option 2: Full Setup (Enhanced Version)

```bash
# 1. Install all dependencies
pip install -r requirements.txt

# 2. Start MongoDB & Monitoring (Docker)
docker-compose -f docker-compose.monitoring.yml up -d

# 3. Configure .env
cp .env.example .env
# Edit .env with:
# - GOOGLE_API_KEY
# - MONGODB_URI
# - TRACE_EXPORTER=jaeger
# - LOG_LEVEL=INFO

# 4. Run enhanced agents
python recommendation-agent/agent_enhanced.py   # Terminal 1
python inventory-agent/agent_enhanced.py        # Terminal 2
python fulfillment-agent/agent.py              # Terminal 3 (use standard)
python payment-agent/agent.py                  # Terminal 4 (use standard)
python post_purchase_agent/agent.py            # Terminal 5 (use standard)
python loyalty-agent/agent.py                  # Terminal 6 (use standard)
python main_enhanced.py                        # Terminal 7
```

### Option 3: Hybrid Approach

Mix standard and enhanced versions based on needs:

```bash
# Use enhanced for high-value services
python recommendation-agent/agent_enhanced.py  # Enhanced (user profiles)
python inventory-agent/agent_enhanced.py       # Enhanced (stock tracking)

# Use standard for simpler services
python fulfillment-agent/agent.py             # Standard
python payment-agent/agent.py                 # Standard
python post_purchase_agent/agent.py           # Standard
python loyalty-agent/agent.py                 # Standard

# Use enhanced main agent
python main_enhanced.py
```

## Environment Variables Explained

### Standard Version (.env)
```bash
GOOGLE_API_KEY=your_gemini_api_key
USER_ID=user_12345
```

### Enhanced Version (.env)
```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key
MONGODB_URI=mongodb://localhost:27017/

# Optional (with defaults)
USER_ID=user_12345
TRACE_EXPORTER=console        # console|jaeger|otlp
JAEGER_HOST=localhost
JAEGER_PORT=6831
LOG_LEVEL=INFO
LOG_TO_FILE=false
ENVIRONMENT=development
SERVICE_VERSION=1.0.0
```

## Monitoring Access (Enhanced Version Only)

After starting the Docker monitoring stack:

- **MongoDB:** `localhost:27017`
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (admin/admin123)
- **Jaeger UI:** http://localhost:16686

Each agent exposes metrics at:
- Recommendation: http://localhost:5002/metrics
- Inventory: http://localhost:5003/metrics
- etc.

## Data Persistence Differences

### Standard Version
```python
# Conversations stored in-memory
user_sessions = {}  # Lost on restart

# User profiles are mock data
user_profiles = {
    "user_12345": {...}
}
```

### Enhanced Version
```python
# Conversations stored in MongoDB
conversations_collection.insert_one({
    "session_id": "...",
    "user_id": "...",
    "messages": [...]
})

# User profiles in MongoDB
user_profiles_collection.insert_one({
    "user_id": "...",
    "preferences": [...],
    "purchase_history": [...]
})
```

## Code Differences Example

### Standard Agent (agent.py)
```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/get-recommendations', methods=['POST'])
def get_recommendations():
    data = request.json
    # Simple logic
    result = generate_recommendations(data)
    return jsonify(result)

if __name__ == '__main__':
    app.run(port=5002)
```

### Enhanced Agent (agent_enhanced.py)
```python
from flask import Flask, request, jsonify
from database.mongodb_config import get_db_manager
from monitoring.tracing import TracingManager
from monitoring.metrics import MetricsManager
from monitoring.logging_config import StructuredLogger

# Initialize monitoring
tracing = TracingManager("service-name")
metrics = MetricsManager("service-name")
logger = StructuredLogger("service-name").get_logger()
db = get_db_manager()

app = Flask(__name__)
tracing.instrument_flask_app(app)
metrics.create_metrics_endpoint(app)

@app.route('/get-recommendations', methods=['POST'])
def get_recommendations():
    start_time = time.time()
    data = request.json

    # Database operations
    user = db.get_collection("users").find_one({"id": data["user_id"]})

    # Traced logic
    with tracing.create_span("generate_recs"):
        result = generate_recommendations(data, user)

    # Record metrics
    duration = time.time() - start_time
    metrics.record_request("POST", "/get-recommendations", 200, duration)

    # Structured logging
    logger.info("Recommendations generated", extra={"user_id": data["user_id"]})

    return jsonify(result)
```

## Rollback Procedure

If enhanced version has issues:

```bash
# Stop enhanced agents
# Use standard versions instead

python recommendation-agent/agent.py  # Instead of agent_enhanced.py
python inventory-agent/agent.py       # Instead of agent_enhanced.py
python main.py                        # Instead of main_enhanced.py
```

No data loss - MongoDB data remains available for future use.

## Gradual Migration Strategy

### Week 1: Testing
- Run standard version in production
- Run enhanced version in staging
- Compare behavior

### Week 2: Monitoring
- Add monitoring to 1-2 agents
- Collect baseline metrics
- Set up Grafana dashboards

### Week 3: Database
- Enable MongoDB for conversations
- Test persistence across restarts
- Verify data integrity

### Week 4: Full Migration
- Switch all agents to enhanced versions
- Enable full monitoring
- Monitor closely for issues

## Troubleshooting

### "ModuleNotFoundError: No module named 'opentelemetry'"
```bash
# Install monitoring dependencies
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-flask
```

### "Cannot connect to MongoDB"
```bash
# Check MongoDB is running
docker ps | grep mongodb

# Or start manually
docker-compose -f docker-compose.monitoring.yml up -d mongodb
```

### "Metrics not showing in Prometheus"
```bash
# Verify metrics endpoint
curl http://localhost:5002/metrics

# Check Prometheus targets
# Open http://localhost:9090/targets
```

## Best Practices

1. **Start Simple:** Use standard version first to understand the system
2. **Test Locally:** Run enhanced version with Docker locally before production
3. **Monitor Gradually:** Add monitoring to one service at a time
4. **Backup Data:** Regularly backup MongoDB collections
5. **Use Hybrid:** Mix standard and enhanced based on criticality

## Support & Documentation

- Standard version: See [README.md](README.md)
- Enhanced version: See [MONITORING_SETUP.md](MONITORING_SETUP.md)
- Architecture: See [ARCHITECTURE.md](ARCHITECTURE.md)

## Summary

✅ **Standard Version:** Fast setup, minimal dependencies, perfect for development
✅ **Enhanced Version:** Production-ready, full observability, requires infrastructure
✅ **Both Versions:** Can coexist, choose based on your needs
✅ **Easy Migration:** Switch between versions anytime

Choose the version that fits your current needs!
