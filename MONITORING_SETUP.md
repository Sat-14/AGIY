# MongoDB & Monitoring Setup Guide

## Overview

This guide covers the setup of MongoDB database integration and comprehensive monitoring/observability for the Sales Agent multi-agent system.

## Table of Contents

1. [MongoDB Integration](#mongodb-integration)
2. [Distributed Tracing](#distributed-tracing)
3. [Metrics Collection](#metrics-collection)
4. [Centralized Logging](#centralized-logging)
5. [Quick Start with Docker](#quick-start-with-docker)
6. [Manual Setup](#manual-setup)
7. [Monitoring Dashboard](#monitoring-dashboard)

---

## MongoDB Integration

### Database Schema

The system uses the following MongoDB collections:

#### 1. `user_profiles`
```javascript
{
  user_id: "string (unique)",
  preferences: ["casual", "denim"],
  size: "M",
  purchase_history: ["SKU_001"],
  browsing_history: ["jackets"],
  loyalty_tier: "silver",
  loyalty_points: 500,
  created_at: ISODate(),
  updated_at: ISODate()
}
```

#### 2. `conversations`
```javascript
{
  session_id: "uuid",
  user_id: "user_12345",
  messages: [
    {
      role: "human|ai",
      content: "message text",
      timestamp: ISODate(),
      metadata: {}
    }
  ],
  timestamp: ISODate(),
  active: true
}
```

#### 3. `inventory`
```javascript
{
  product_id: "SKU_JCK_01",
  name: "Denim Trucker Jacket",
  category: "jackets",
  price: 4999,
  currency: "INR",
  tags: ["casual", "denim"],
  warehouses: [{
    warehouse_id: "WH_NORTH",
    stock_level: 150,
    location: "Delhi NCR"
  }],
  stores: [{
    store_id: "STORE_SCW_DL",
    stock_level: 5,
    city: "Delhi"
  }],
  last_updated: ISODate()
}
```

#### 4. `orders`
```javascript
{
  order_id: "ORD-12345",
  user_id: "user_12345",
  items: [{
    product_id: "SKU_JCK_01",
    quantity: 1,
    price: 4999
  }],
  total_amount: 4999,
  currency: "INR",
  status: "delivered",
  tracking_number: "TRK123",
  estimated_delivery: ISODate(),
  created_at: ISODate()
}
```

#### 5. `transactions`
```javascript
{
  transaction_id: "TXN-20251015-1234",
  user_id: "user_12345",
  cart_id: "CART_001",
  amount: 4999,
  currency: "INR",
  status: "completed",
  payment_method: "credit_card",
  gateway_response: {},
  created_at: ISODate()
}
```

### Environment Variables

Add to your `.env` file:

```bash
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/
# Or for authenticated connection:
# MONGODB_URI=mongodb://username:password@localhost:27017/sales_agent_db

# Monitoring Configuration
TRACE_EXPORTER=jaeger  # Options: console, jaeger, otlp
JAEGER_HOST=localhost
JAEGER_PORT=6831
OTLP_ENDPOINT=http://localhost:4317

LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_DIR=logs

ENVIRONMENT=development  # or production
SERVICE_VERSION=1.0.0
```

---

## Distributed Tracing

### OpenTelemetry Integration

The system uses OpenTelemetry for distributed tracing across all microservices.

**Features:**
- End-to-end request tracing
- Service dependency mapping
- Performance bottleneck identification
- Cross-service context propagation

**Supported Exporters:**
1. **Console** (development) - Logs traces to console
2. **Jaeger** (recommended) - Full tracing UI
3. **OTLP** (production) - Compatible with Tempo, Zipkin, etc.

**Usage in Code:**

```python
from monitoring.tracing import TracingManager, trace_function

# Initialize tracing
tracing = TracingManager("my-service", "1.0.0")

# Instrument Flask app
tracing.instrument_flask_app(app)

# Trace functions
@trace_function
def my_function():
    pass

# Create custom spans
with tracing.create_span("custom_operation") as span:
    span.set_attribute("user_id", "123")
    # Do work
```

---

## Metrics Collection

### Prometheus Integration

The system exposes Prometheus metrics at `/metrics` endpoint on each service.

**Available Metrics:**

#### Request Metrics
- `http_requests_total` - Total HTTP requests (counter)
- `http_request_duration_seconds` - Request duration (histogram)
- `http_request_size_bytes` - Request size (histogram)
- `http_response_size_bytes` - Response size (histogram)

#### Agent Metrics
- `agent_calls_total` - Inter-agent calls (counter)
- `agent_call_duration_seconds` - Agent call duration (histogram)

#### Business Metrics
- `recommendations_generated_total` - Recommendations count
- `inventory_checks_total` - Inventory checks count
- `transactions_initiated_total` - Transactions initiated
- `transactions_completed_total` - Successful transactions
- `reservations_made_total` - Store reservations
- `orders_tracked_total` - Order status queries

#### Database Metrics
- `database_operations_total` - DB operations (counter)
- `database_operation_duration_seconds` - DB operation duration (histogram)

#### System Metrics
- `active_sessions` - Active user sessions (gauge)
- `cache_hit_rate` - Cache hit rate percentage (gauge)
- `errors_total` - Total errors (counter)

**Usage in Code:**

```python
from monitoring.metrics import MetricsManager

# Initialize metrics
metrics = MetricsManager("my-service")

# Create /metrics endpoint
metrics.create_metrics_endpoint(app)

# Record metrics
metrics.record_request("POST", "/api/endpoint", 200, duration)
metrics.record_agent_call("source", "target", "/endpoint", "success", duration)
metrics.record_db_operation("collection", "find", "success", duration)
```

---

## Centralized Logging

### Structured JSON Logging

All services use structured JSON logging with trace context propagation.

**Log Format:**
```json
{
  "timestamp": "2025-10-17T10:30:00.000Z",
  "level": "INFO",
  "service": "recommendation-agent",
  "trace_id": "abc123...",
  "span_id": "def456...",
  "message": "API Request",
  "event": "api_request",
  "method": "POST",
  "endpoint": "/get-recommendations",
  "filename": "agent.py",
  "function": "get_recommendations",
  "line": 42
}
```

**Usage in Code:**

```python
from monitoring.logging_config import (
    StructuredLogger,
    log_api_request,
    log_api_response,
    log_business_event,
    log_error
)

# Initialize logger
logging_config = StructuredLogger("my-service")
logger = logging_config.get_logger()

# Log events
log_api_request(logger, "POST", "/api/endpoint", params)
log_api_response(logger, "POST", "/api/endpoint", 200, duration)
log_business_event(logger, "recommendation_generated", user_id="123")
log_error(logger, exception, context)
```

---

## Quick Start with Docker

### 1. Start Monitoring Stack

```bash
# Start MongoDB, Prometheus, Grafana, Jaeger
docker-compose -f docker-compose.monitoring.yml up -d
```

**Access URLs:**
- MongoDB: `localhost:27017`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (admin/admin123)
- Jaeger UI: `http://localhost:16686`
- Loki: `http://localhost:3100`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Update Environment Variables

```bash
# Update .env file
MONGODB_URI=mongodb://admin:password123@localhost:27017/sales_agent_db
TRACE_EXPORTER=jaeger
LOG_LEVEL=INFO
```

### 4. Run Enhanced Agents

```bash
# Terminal 1 - Main Sales Agent (enhanced)
python main_enhanced.py

# Terminal 2 - Recommendation Agent (enhanced)
python recommendation-agent/agent_enhanced.py

# Terminal 3 - Inventory Agent (enhanced)
python inventory-agent/agent_enhanced.py

# Repeat for other agents...
```

---

## Manual Setup

### 1. Install MongoDB

**macOS:**
```bash
brew tap mongodb/brew
brew install mongodb-community@7.0
brew services start mongodb-community@7.0
```

**Ubuntu/Debian:**
```bash
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo systemctl start mongod
```

**Windows:**
Download installer from [MongoDB Download Center](https://www.mongodb.com/try/download/community)

### 2. Install Prometheus

```bash
# Download Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.48.0/prometheus-2.48.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*

# Copy config
cp monitoring/prometheus_config.yml ./prometheus.yml

# Run
./prometheus --config.file=prometheus.yml
```

### 3. Install Grafana

```bash
# Ubuntu/Debian
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo apt-get update
sudo apt-get install grafana
sudo systemctl start grafana-server

# macOS
brew install grafana
brew services start grafana
```

### 4. Install Jaeger

```bash
# Using Docker (recommended)
docker run -d --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 6831:6831/udp \
  -p 16686:16686 \
  -p 14268:14268 \
  jaegertracing/all-in-one:latest
```

---

## Monitoring Dashboard

### Grafana Setup

1. **Access Grafana:** `http://localhost:3000`
2. **Login:** admin/admin123
3. **Add Prometheus Data Source:**
   - Configuration → Data Sources → Add Data Source
   - Select Prometheus
   - URL: `http://localhost:9090`
   - Click "Save & Test"

4. **Import Dashboard:**
   - Dashboards → Import
   - Upload `monitoring/grafana_dashboard.json`
   - Select Prometheus data source
   - Click "Import"

### Dashboard Panels

1. **Total Requests per Service** - Request volume by service
2. **Request Duration (P95)** - 95th percentile latency
3. **Error Rate** - Errors by service and type
4. **Active Sessions** - Current active user sessions
5. **Agent Call Flow** - Inter-agent communication patterns
6. **Database Operations** - MongoDB operation metrics
7. **Business Metrics** - Recommendations, transactions, reservations
8. **Cache Hit Rate** - Cache performance

### Jaeger Tracing

1. **Access Jaeger:** `http://localhost:16686`
2. **Search Traces:**
   - Select service (e.g., "sales-agent")
   - Set time range
   - Click "Find Traces"
3. **Analyze Trace:**
   - Click on a trace to see full request flow
   - View span duration, tags, logs
   - Identify bottlenecks

---

## Key Files

### Database
- `database/mongodb_config.py` - MongoDB connection and schema

### Monitoring
- `monitoring/tracing.py` - OpenTelemetry tracing setup
- `monitoring/metrics.py` - Prometheus metrics
- `monitoring/logging_config.py` - Structured logging
- `monitoring/prometheus_config.yml` - Prometheus configuration
- `monitoring/grafana_dashboard.json` - Grafana dashboard

### Enhanced Agents
- `main_enhanced.py` - Main sales agent with DB & monitoring
- `recommendation-agent/agent_enhanced.py` - Enhanced recommendation agent
- `inventory-agent/agent_enhanced.py` - Enhanced inventory agent

### Configuration
- `docker-compose.monitoring.yml` - Complete monitoring stack
- `.env` - Environment variables

---

## Metrics Endpoints

All enhanced agents expose metrics at:

- Sales Agent: `http://localhost:8000/metrics`
- Recommendation: `http://localhost:5002/metrics`
- Inventory: `http://localhost:5003/metrics`
- Fulfillment: `http://localhost:5001/metrics`
- Payment: `http://localhost:5005/metrics`
- Post-Purchase: `http://localhost:5004/metrics`
- Loyalty: `http://localhost:5006/metrics`

---

## Troubleshooting

### MongoDB Connection Issues

```bash
# Check MongoDB status
systemctl status mongod  # Linux
brew services list       # macOS

# Test connection
mongosh mongodb://localhost:27017
```

### Prometheus Not Scraping

```bash
# Check targets
Open http://localhost:9090/targets

# Verify metrics endpoint
curl http://localhost:5002/metrics
```

### Jaeger No Traces

```bash
# Check environment variables
echo $TRACE_EXPORTER  # Should be "jaeger"
echo $JAEGER_HOST     # Should be "localhost"

# Verify Jaeger is running
docker ps | grep jaeger
```

### Grafana Dashboard Issues

```bash
# Check Prometheus data source
Configuration → Data Sources → Test

# Verify Prometheus is running
curl http://localhost:9090/api/v1/status/config
```

---

## Production Considerations

### Security
- [ ] Enable MongoDB authentication
- [ ] Use TLS/SSL for MongoDB connections
- [ ] Secure Prometheus/Grafana with authentication
- [ ] Use secrets management (Vault, AWS Secrets Manager)

### Performance
- [ ] Set up MongoDB replica sets
- [ ] Configure Prometheus retention policies
- [ ] Set up Grafana alerting
- [ ] Implement log rotation

### Scalability
- [ ] Deploy MongoDB Atlas (managed service)
- [ ] Use Prometheus remote write to long-term storage
- [ ] Set up Grafana Loki for log aggregation
- [ ] Configure trace sampling in production

---

## Next Steps

1. **Populate MongoDB:** Add sample data to collections
2. **Create Alerts:** Set up Prometheus alerting rules
3. **Custom Dashboards:** Create service-specific Grafana dashboards
4. **Load Testing:** Test system under load and monitor metrics
5. **SLA Definition:** Define SLOs based on metrics

---

## Support

For issues or questions:
- Check logs: `logs/` directory
- View traces: Jaeger UI
- Check metrics: Prometheus UI
- Review dashboards: Grafana

---

**Built with observability in mind for production-ready AI systems**
