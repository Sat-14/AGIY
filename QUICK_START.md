# Quick Start Guide

## Choose Your Version

### 🚀 Option 1: Standard Version (2 minutes)
**Best for:** Testing, learning, local development

```bash
# 1. Install dependencies
pip install langchain langchain-google-genai python-dotenv requests flask

# 2. Set API key
echo "GOOGLE_API_KEY=your_key_here" > .env

# 3. Start services (7 terminals)
python recommendation-agent/agent.py   # Port 5002
python inventory-agent/agent.py        # Port 5003
python fulfillment-agent/agent.py      # Port 5001
python payment-agent/agent.py          # Port 5005
python post_purchase_agent/agent.py    # Port 5004
python loyalty-agent/agent.py          # Port 5006
python main.py                         # Main agent

# 4. Chat!
You: Hi, I'm looking for a casual jacket
```

### 🏢 Option 2: Enhanced Version (15 minutes)
**Best for:** Production, monitoring, persistence

```bash
# 1. Install all dependencies
pip install -r requirements.txt

# 2. Start infrastructure (Docker required)
docker-compose -f docker-compose.monitoring.yml up -d

# 3. Configure environment
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY and settings

# 4. Start enhanced services
python recommendation-agent/agent_enhanced.py   # Port 5002
python inventory-agent/agent_enhanced.py        # Port 5003
# ... other agents (use standard versions for now)
python main_enhanced.py                         # Main agent

# 5. Access monitoring
# MongoDB: localhost:27017
# Grafana: http://localhost:3000 (admin/admin123)
# Jaeger: http://localhost:16686
# Prometheus: http://localhost:9090
```

## Test the System

### Example Conversation
```
You: Hi, I need a jacket for winter
Ria: I'd be happy to help! What's your preferred style?

You: Something casual and blue
Ria: [Calls recommendation agent, shows products]

You: Check stock for the Denim Jacket in Delhi, size M
Ria: [Calls inventory agent, shows availability]

You: Reserve it at Select Citywalk store
Ria: [Calls fulfillment agent, creates reservation]
```

## Verify Everything Works

### Check Services Running
```bash
curl http://localhost:5002/get-recommendations -X POST \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_12345","context":"jacket","count":3}'
```

### View Metrics (Enhanced only)
```bash
curl http://localhost:5002/metrics
```

## Next Steps

- Read [README.md](README.md) for full documentation
- See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) to understand versions
- Check [MONITORING_SETUP.md](MONITORING_SETUP.md) for observability setup
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design

## Troubleshooting

**Can't install dependencies?**
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**MongoDB connection error?**
```bash
docker-compose -f docker-compose.monitoring.yml up -d mongodb
```

**Agent not responding?**
Check all agents are running on correct ports (5001-5006)

---

**Happy Selling! 🛍️**
