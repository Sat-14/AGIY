# Multi-Agent Fashion Retail AI System

A sophisticated multi-agent conversational AI system for ABFRL (Aditya Birla Fashion and Retail) that demonstrates enterprise-grade AI architecture using specialized agents communicating via REST APIs.

---

## 📋 Table of Contents

- [System Overview](#system-overview)
- [Architecture](#architecture)
- [Agent Specifications](#agent-specifications)
- [Technology Stack](#technology-stack)
- [Features](#features)
- [Setup Instructions](#setup-instructions)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [System Flow](#system-flow)
- [Future Enhancements](#future-enhancements)

---

## 🎯 System Overview

This project implements a **multi-agent AI system** where specialized agents handle different aspects of the e-commerce customer journey. The system uses a **microservices architecture** where each agent is an independent service that communicates via REST APIs.

### Key Concept

Instead of a monolithic AI system, we have:
- **1 Main Conversational Agent** (Sales Agent - "Ria") that orchestrates everything
- **3 Specialized Backend Agents** that handle specific domain tasks
- **Agent-to-Agent Communication** via HTTP REST APIs

This mirrors real-world enterprise systems where different departments (inventory, recommendations, fulfillment) operate independently but communicate seamlessly.

---

## 🏗️ Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         USER                                │
│                     (CLI Interface)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   SALES AGENT (Ria)                         │
│              LangChain + Google Gemini                      │
│           ┌─────────────────────────────┐                   │
│           │  Conversation Memory        │                   │
│           │  Tool Selection Logic       │                   │
│           │  Context Management         │                   │
│           └─────────────────────────────┘                   │
└───┬─────────────┬──────────────┬──────────────┬─────────────┘
    │             │              │              │
    │ REST API    │ REST API     │ REST API     │ REST API
    │ Port 5002   │ Port 5003    │ Port 5001    │ (Mock)
    ▼             ▼              ▼              ▼
┌─────────┐  ┌─────────┐   ┌─────────┐   ┌─────────┐
│Recommend│  │Inventory│   │Fulfill- │   │Payment/ │
│-ation   │  │Agent    │   │ment     │   │Loyalty  │
│Agent    │  │         │   │Agent    │   │Agents   │
└─────────┘  └─────────┘   └─────────┘   └─────────┘
     │            │              │
     ▼            ▼              ▼
┌─────────┐  ┌─────────┐   ┌─────────┐
│User     │  │Warehouse│   │Store    │
│Profile  │  │Database │   │System   │
│DB       │  │         │   │         │
└─────────┘  └─────────┘   └─────────┘
```

### Directory Structure

```
Sales-Agent/
├── main.py                          # Main Sales Agent (Ria)
├── tools.py                         # Agent tool definitions
├── check_models.py                  # Gemini API validator
├── requirements.txt                 # Python dependencies
├── .env                            # Environment variables (API keys)
│
├── recommendation-agent/
│   └── agent.py                    # Port 5002 - Recommendation service
│
├── inventory-agent/
│   └── agent.py                    # Port 5003 - Inventory service
│
├── fulfillment-agent/
│   └── agent.py                    # Port 5001 - Fulfillment service
│
└── *.JSON                          # API contract specifications
```

---

## 🤖 Agent Specifications

### 1. Sales Agent (Ria) - Main Orchestrator

**Technology:** LangChain + Google Gemini Pro
**Type:** Conversational AI with tool-calling capabilities
**Port:** N/A (CLI interface)

**Responsibilities:**
- Natural language understanding and conversation
- User intent recognition
- Tool selection and orchestration
- Context and memory management
- Response generation

**Key Features:**
- **Memory System**: Maintains conversation history per user session using `ConversationBufferMemory`
- **Tool Calling**: Automatically selects and invokes appropriate backend agents
- **Context Awareness**: Understands multi-turn conversations
- **User Session Management**: Stores and retrieves user conversation state

**Implementation Details:**
```python
# Uses LangChain's AgentExecutor with:
- ChatGoogleGenerativeAI (LLM)
- ConversationBufferMemory (Memory)
- create_tool_calling_agent (Agent Framework)
- 6 available tools for different operations
```

---

### 2. Recommendation Agent

**Technology:** Flask REST API
**Port:** 5002
**Endpoint:** `/get-recommendations`

**Core Functionality:**

#### a) Customer Profile Analysis
```python
{
  "preferences": ["casual", "denim", "blue"],
  "size": "M",
  "purchase_history": ["SKU_TSH_01"],
  "browsing_history": ["jackets", "shirts"]
}
```
- Retrieves stored user preferences
- Analyzes past purchase behavior
- Considers browsing patterns

#### b) Seasonal Trend Analysis
```python
- Winter (Dec-Feb): jackets, hoodies, sweaters
- Spring (Mar-May): light jackets, t-shirts
- Summer (Jun-Aug): summer wear, shorts
- Fall (Sep-Nov): transitional wear, layering
```
- Dynamically adjusts recommendations based on current season
- Promotes weather-appropriate products

#### c) Context-Based Scoring Algorithm
```python
Score Calculation:
- Context keyword match: +5 points
- Tag match: +3 points
- User preference match: +2 points
- Seasonal relevance: +1 point
```
- Ranks products by relevance score
- Returns top N products

#### d) Bundle Suggestions
```json
{
  "bundleName": "Complete Casual Look",
  "products": ["SKU_JCK_01", "SKU_TSH_01", "SKU_CHN_01"],
  "discount": "15% OFF",
  "totalPrice": 8997
}
```

**API Request:**
```json
POST http://127.0.0.1:5002/get-recommendations
{
  "user_id": "user_12345",
  "context": "casual blue jacket",
  "count": 3
}
```

**API Response:**
```json
{
  "status": "success",
  "recommendations": [
    {
      "productId": "SKU_JCK_01",
      "name": "Denim Trucker Jacket",
      "price": {"amount": 4999, "currency": "INR"},
      "imageUrl": "...",
      "tags": ["casual", "denim", "blue"]
    }
  ],
  "bundles": [...],
  "promotions": ["NEW_USER_20", "SEASONAL_SALE"]
}
```

---

### 3. Inventory Agent

**Technology:** Flask REST API
**Port:** 5003
**Endpoint:** `/check-inventory`

**Core Functionality:**

#### a) Multi-Warehouse Inventory
```python
Warehouses:
- WH_NORTH (Delhi NCR) - 150 units
- WH_SOUTH (Bangalore) - 80 units
- WH_WEST (Mumbai) - 120 units
- WH_EAST (Kolkata) - 60 units
```
- Real-time stock across regional distribution centers
- Estimated shipping times per warehouse

#### b) Physical Store Availability
```python
Stores:
- Select Citywalk (Delhi) - 5 units (LOW)
- DLF Promenade (Delhi) - 2 units (LOW)
- Ambience Mall (Gurgaon) - 8 units (MEDIUM)
- Phoenix Palladium (Mumbai) - 12 units (HIGH)
- UB City Mall (Bangalore) - 6 units (MEDIUM)
```
- Stock levels with descriptors (high/medium/low)
- Location-based filtering (city/region)
- Complete store details (address, store ID)

#### c) Online Status Calculation
```python
Logic:
- total_stock == 0 → "out_of_stock"
- total_stock < 50 → "low_stock"
- total_stock >= 50 → "in_stock"
```

#### d) Fulfillment Options
```json
[
  {
    "type": "ship_to_home",
    "available": true,
    "estimatedDelivery": "2025-10-18",
    "shippingCost": 0
  },
  {
    "type": "click_and_collect",
    "available": true,
    "availableStores": 2,
    "message": "Reserve online and pick up from store"
  },
  {
    "type": "in_store_purchase",
    "available": true,
    "availableStores": 5,
    "message": "Try and buy at our stores"
  }
]
```

**API Request:**
```json
POST http://127.0.0.1:5003/check-inventory
{
  "product_id": "SKU_JCK_01",
  "attributes": {"size": "M", "color": "blue"},
  "location_context": {"city": "Delhi"}
}
```

**API Response:**
```json
{
  "status": "success",
  "productId": "SKU_JCK_01",
  "onlineStatus": "in_stock",
  "onlineStockLevel": 410,
  "warehouses": [...],
  "availableStores": [...],
  "fulfillmentOptions": [...],
  "lastUpdated": "2025-10-15T11:43:19.575132"
}
```

---

### 4. Fulfillment Agent

**Technology:** Flask REST API
**Port:** 5001
**Endpoint:** `/reserve-in-store`

**Core Functionality:**

#### In-Store Reservation System
```python
Process:
1. Receives reservation request
2. Validates user_id, product_id, store_id
3. Generates unique reservation ID
4. Creates 24-hour hold on inventory
5. (Would) Notify store staff
```

**Reservation ID Format:**
```
RES-{product_prefix}-{store_prefix}-{user_suffix}
Example: RES-SKU_-STO-2345
```

**API Request:**
```json
POST http://127.0.0.1:5001/reserve-in-store
{
  "user_id": "user_12345",
  "product_id": "SKU_JCK_01",
  "store_id": "STORE_SCW_DL"
}
```

**API Response:**
```json
{
  "status": "success",
  "reservationId": "RES-SKU_-STO-2345",
  "confirmationMessage": "Your item has been reserved for 24 hours."
}
```

**Future Enhancements:**
- Database integration for persistent reservations
- Email/SMS notifications to customers
- Store staff notification system
- Inventory deduction logic
- Expiration handling after 24 hours

---

## 💻 Technology Stack

### Core Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **LLM** | Google Gemini Pro | Natural language understanding & generation |
| **Agent Framework** | LangChain | Tool orchestration, memory, conversation |
| **Backend APIs** | Flask | Microservices for specialized agents |
| **HTTP Client** | Requests | Inter-agent communication |
| **Memory** | ConversationBufferMemory | Session state management |
| **Language** | Python 3.13 | Primary programming language |

### Dependencies

```
langchain              # Agent framework
langchain-google-genai # Google Gemini integration
python-dotenv          # Environment variable management
requests               # HTTP client for API calls
flask                  # Web framework for agent APIs
```

### Why These Technologies?

**LangChain:**
- Industry-standard framework for building LLM applications
- Built-in support for tool calling and memory
- Easy integration with various LLMs
- Production-ready agent executors

**Google Gemini Pro:**
- Advanced reasoning capabilities
- Function calling support
- Cost-effective compared to GPT-4
- Fast response times

**Flask:**
- Lightweight and perfect for microservices
- Easy to deploy and scale
- RESTful API development
- Python ecosystem compatibility

---

##  Features

### Conversational AI Features
-  Multi-turn conversations with context retention
-  Natural language understanding
-  Intent recognition and slot filling
-  Proactive recommendations
-  Error handling and graceful degradation

### Business Features
-  Personalized product recommendations
-  Real-time inventory checking
-  Multi-channel fulfillment options
-  Bundle deals and promotions
-  Store reservation system
-  Seasonal trend analysis

### Technical Features
-  Microservices architecture
-  REST API communication
-  Agent-to-agent orchestration
-  Session management
-  Error handling and retry logic
-  Modular and extensible design

---

## 🚀 Setup Instructions

### Prerequisites

- Python 3.13 or higher
- Google Gemini API Key ([Get it here](https://makersuite.google.com/app/apikey))
- Terminal/Command Prompt

### Step 1: Clone/Download the Project

```bash
cd Sales-Agent
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Create a `.env` file in the project root:

```bash
GOOGLE_API_KEY=your_actual_api_key_here
```

**How to get API key:**
1. Visit https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy and paste into `.env` file

### Step 4: Verify Setup

```bash
python check_models.py
```

Expected output:
```
Successfully configured API key. Fetching available models...
--------------------
Model found: models/gemini-pro-latest
Model found: models/gemini-1.5-flash
...
```

### Step 5: Start All Agents

**Terminal 1 - Fulfillment Agent:**
```bash
cd fulfillment-agent
python agent.py
```
Output: `Running on http://127.0.0.1:5001`

**Terminal 2 - Recommendation Agent:**
```bash
cd recommendation-agent
python agent.py
```
Output: `Running on http://127.0.0.1:5002`

**Terminal 3 - Inventory Agent:**
```bash
cd inventory-agent
python agent.py
```
Output: `Running on http://127.0.0.1:5003`

**Terminal 4 - Sales Agent:**
```bash
python main.py
```
Output: `Hello! I'm Ria. How can I help you today?`

---

## 📱 Usage

### Example Conversation

```
You: Hi! I'm looking for a casual jacket for women.

Ria: I'd love to help! I've found some great options:
     - Denim Trucker Jacket (₹4,999)
     - Classic Biker Jacket (₹8,999)
     - Lightweight Puffer Jacket (₹5,499)

     Plus, we have a "Complete Casual Look" bundle with 15% OFF!

You: Can you check if the Denim Trucker Jacket is available in Delhi, size M?

Ria: Great news! The Denim Trucker Jacket is in stock:

     Online: 410 units available, ships in 2-3 days

     Stores in Delhi:
     - Select Citywalk: 5 left (LOW STOCK!)
     - DLF Promenade: 2 left (LOW STOCK!)

     You can ship to home, reserve for pickup, or buy in-store!

You: Reserve it at Select Citywalk for me.

Ria: Perfect! I've reserved it for you.
     Reservation ID: RES-SKU_-STO-2345
     Valid for: 24 hours
     Store: Select Citywalk, Saket
```

### What Happened Behind the Scenes?

```
1. User Query → Sales Agent (Ria)
2. Ria calls Recommendation Agent API
   ↳ Analyzes user profile + seasonal trends
   ↳ Returns personalized products
3. Ria calls Inventory Agent API
   ↳ Checks 4 warehouses
   ↳ Checks 5 stores
   ↳ Calculates fulfillment options
4. Ria calls Fulfillment Agent API
   ↳ Creates reservation
   ↳ Generates reservation ID
5. Ria responds to user with all information
```

---

## 📡 API Documentation

### Recommendation Agent API

**Endpoint:** `POST http://127.0.0.1:5002/get-recommendations`

**Request Body:**
```json
{
  "user_id": "string (required)",
  "context": "string (required) - e.g., 'casual jacket'",
  "count": "integer (optional, default: 3)"
}
```

**Response:**
```json
{
  "status": "success",
  "recommendations": [
    {
      "productId": "string",
      "name": "string",
      "price": {
        "amount": "number",
        "currency": "string"
      },
      "imageUrl": "string",
      "tags": ["string"]
    }
  ],
  "bundles": [
    {
      "bundleName": "string",
      "products": ["string"],
      "discount": "string",
      "totalPrice": "number"
    }
  ],
  "promotions": ["string"]
}
```

---

### Inventory Agent API

**Endpoint:** `POST http://127.0.0.1:5003/check-inventory`

**Request Body:**
```json
{
  "product_id": "string (required)",
  "attributes": {
    "size": "string (optional)",
    "color": "string (optional)"
  },
  "location_context": {
    "city": "string (optional)"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "productId": "string",
  "onlineStatus": "in_stock|low_stock|out_of_stock",
  "onlineStockLevel": "number",
  "warehouses": [
    {
      "warehouseId": "string",
      "warehouseName": "string",
      "location": "string",
      "stockLevel": "number",
      "estimatedShippingTime": "string"
    }
  ],
  "availableStores": [
    {
      "storeId": "string",
      "storeName": "string",
      "address": "string",
      "city": "string",
      "region": "string",
      "stockLevel": "number",
      "stockDescriptor": "high|medium|low"
    }
  ],
  "fulfillmentOptions": [
    {
      "type": "ship_to_home|click_and_collect|in_store_purchase",
      "available": "boolean",
      "estimatedDelivery": "date (optional)",
      "shippingCost": "number (optional)",
      "availableStores": "number (optional)",
      "message": "string (optional)"
    }
  ],
  "lastUpdated": "ISO 8601 timestamp"
}
```

---

### Fulfillment Agent API

**Endpoint:** `POST http://127.0.0.1:5001/reserve-in-store`

**Request Body:**
```json
{
  "user_id": "string (required)",
  "product_id": "string (required)",
  "store_id": "string (required)"
}
```

**Response:**
```json
{
  "status": "success|error",
  "reservationId": "string",
  "confirmationMessage": "string"
}
```

---

## 🔄 System Flow

### Complete User Journey Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. USER: "I need a jacket"                             │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 2. SALES AGENT: Receives & understands intent          │
│    - LangChain processes input                         │
│    - Identifies need for recommendations               │
│    - Prepares tool call                                │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼ POST /get-recommendations
┌─────────────────────────────────────────────────────────┐
│ 3. RECOMMENDATION AGENT:                               │
│     Loads user profile (preferences, history)         │
│     Checks current season (Oct = Fall)                │
│     Scores products by relevance                      │
│     Generates bundle offers                           │
│     Returns top 3 products + promotions               │
└────────────────┬────────────────────────────────────────┘
                 │ Returns JSON
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 4. SALES AGENT: Formats response                       │
│    "I found 3 jackets for you: ..."                    │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 5. USER: "Check stock for SKU_JCK_01 in Delhi, M"     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼ POST /check-inventory
┌─────────────────────────────────────────────────────────┐
│ 6. INVENTORY AGENT:                                    │
│     Queries 4 warehouses → 410 total units           │
│     Filters stores by Delhi → 2 stores found         │
│     Calculates online status → "in_stock"            │
│     Determines fulfillment options → 3 options        │
│     Adds last updated timestamp                       │
└────────────────┬────────────────────────────────────────┘
                 │ Returns JSON
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 7. SALES AGENT: Formats response                       │
│    "In stock! 5 at Citywalk, 2 at DLF..."             │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 8. USER: "Reserve at Citywalk"                        │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼ POST /reserve-in-store
┌─────────────────────────────────────────────────────────┐
│ 9. FULFILLMENT AGENT:                                  │
│     Validates product/store/user                      │
│     Generates reservation ID                          │
│     Creates 24-hour hold                              │
│     (Would) Notify store staff                        │
└────────────────┬────────────────────────────────────────┘
                 │ Returns JSON
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 10. SALES AGENT: Confirms reservation                  │
│     "Reserved! ID: RES-SKU_-STO-2345"                  │
└─────────────────────────────────────────────────────────┘
```

---

## 🎓 Key Technical Concepts for Presentation

### 1. Agent-Based Architecture

**What is it?**
- System decomposed into autonomous agents
- Each agent has a specific responsibility
- Agents communicate via well-defined interfaces (APIs)

**Benefits:**
- **Scalability**: Scale individual agents independently
- **Maintainability**: Changes to one agent don't affect others
- **Testability**: Each agent can be tested in isolation
- **Resilience**: If one agent fails, others continue working

### 2. LangChain Tool Calling

**What is it?**
LangChain allows LLMs to use "tools" - external functions the AI can invoke.

**How it works:**
```python
1. LLM receives user input
2. LLM decides which tool(s) to use
3. LLM generates function call with parameters
4. Tool executes and returns result
5. LLM uses result to generate response
```

**Example:**
```
User: "Check stock for SKU_JCK_01"
LLM thinks: "I need to use check_inventory tool"
LLM calls: check_inventory(product_id="SKU_JCK_01", location="Delhi")
Tool returns: {stock: 410, stores: [...]}
LLM responds: "Great news! We have 410 units..."
```

### 3. Conversation Memory

**What is it?**
System that maintains context across multiple conversation turns.

**Implementation:**
```python
ConversationBufferMemory stores:
- Previous user messages
- Previous AI responses
- Conversation metadata
```

**Why it matters:**
```
Without memory:
User: "Show me jackets"
AI: [shows jackets]
User: "What colors?"
AI: "What colors for what?" ❌

With memory:
User: "Show me jackets"
AI: [shows jackets]
User: "What colors?"
AI: "The Denim Trucker comes in blue and black" 
```

### 4. Microservices Communication

**REST API Pattern:**
- Each agent exposes HTTP endpoints
- Agents communicate using JSON
- Stateless request/response model
- Standard HTTP methods (POST)

**Benefits:**
- Language agnostic (can use Python, Node.js, Java, etc.)
- Easy to debug (can test with curl/Postman)
- Industry standard
- Cloud-ready

---

## 🔮 Future Enhancements

### Phase 1: Data Persistence
- [ ] PostgreSQL/MongoDB for user profiles
- [ ] Redis for session caching
- [ ] Persistent reservation storage
- [ ] Order history database

### Phase 2: Advanced AI Features
- [ ] Vector database for semantic search
- [ ] RAG (Retrieval Augmented Generation) for product knowledge
- [ ] Sentiment analysis for customer satisfaction
- [ ] Multi-language support

### Phase 3: Enterprise Features
- [ ] Authentication & authorization (JWT)
- [ ] Rate limiting and API quotas
- [ ] Logging and monitoring (ELK stack)
- [ ] Analytics dashboard
- [ ] A/B testing framework

### Phase 4: Integration
- [ ] Payment gateway integration
- [ ] Shipping provider APIs
- [ ] Email/SMS notifications
- [ ] CRM system integration
- [ ] Analytics and BI tools

### Phase 5: Scalability
- [ ] Containerization (Docker)
- [ ] Kubernetes orchestration
- [ ] Load balancing
- [ ] Horizontal scaling
- [ ] CDN for static assets

### Phase 6: User Experience
- [ ] Web UI (React/Vue)
- [ ] Mobile app (React Native)
- [ ] Voice interface (Alexa/Google Assistant)
- [ ] WhatsApp/Telegram bot
- [ ] AR try-on features

---

## 🎯 Business Value

### For Customers
- **Personalized Experience**: AI understands preferences and history
- **Multi-Channel Options**: Buy online, pick up in-store, or shop in-person
- **Real-Time Information**: Live inventory updates
- **24/7 Availability**: AI assistant always available
- **Seamless Journey**: From discovery to purchase

### For Business
- **Increased Conversion**: Personalized recommendations boost sales
- **Reduced Support Cost**: AI handles common queries
- **Better Inventory Management**: Real-time visibility
- **Customer Insights**: Analytics on preferences and behavior
- **Competitive Advantage**: Modern, tech-forward brand image

### Metrics to Track
- Conversion rate improvement
- Average order value increase
- Customer satisfaction score
- Response time reduction
- Support ticket reduction

---

## 🛠️ Troubleshooting

### Common Issues

**Issue: "Could not connect to recommendation service"**
```
Solution: Ensure Recommendation Agent is running on port 5002
Check: Run 'curl http://127.0.0.1:5002/get-recommendations'
```

**Issue: "API key not found"**
```
Solution: Create .env file with GOOGLE_API_KEY=your_key
Verify: Run 'python check_models.py'
```

**Issue: "Port already in use"**
```
Solution: Kill the process using the port
Windows: netstat -ano | findstr :5002
Linux/Mac: lsof -ti:5002 | xargs kill
```

**Issue: "Dependency conflicts"**
```
Solution: Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## 📊 Presentation Talking Points

### For Technical Audience

1. **Architecture**: Multi-agent microservices with REST communication
2. **LLM Integration**: LangChain tool-calling with Gemini Pro
3. **Scalability**: Each agent can scale independently
4. **Modularity**: Easy to add new agents or modify existing ones
5. **Production Ready**: Error handling, logging, validation

### For Business Audience

1. **Customer Experience**: Personalized, 24/7 AI shopping assistant
2. **Omnichannel**: Seamless online and offline integration
3. **Efficiency**: Automated recommendations and inventory checks
4. **ROI**: Reduced support costs, increased conversion
5. **Innovation**: Cutting-edge AI technology

### Demo Script

1. **Introduction** (2 min)
   - Show architecture diagram
   - Explain multi-agent concept

2. **Live Demo** (5 min)
   - Start conversation: "I need a jacket"
   - Show recommendations with bundles
   - Check inventory with multiple options
   - Make reservation
   - Highlight agent communication in logs

3. **Technical Deep Dive** (3 min)
   - Show code for one agent
   - Explain API contract
   - Demonstrate tool calling

4. **Business Value** (2 min)
   - Metrics and KPIs
   - Customer benefits
   - Competitive advantage

---

## 📝 License

This project is a prototype for educational and demonstration purposes.

---

## 👥 Contact

For questions or support regarding this system, please contact the development team.

---

## 🙏 Acknowledgments

- **LangChain**: Agent framework and orchestration
- **Google Gemini**: Large Language Model
- **Flask**: Microservices framework
- **ABFRL**: Business use case and requirements

---

**Built with  for the future of AI-powered retail**
