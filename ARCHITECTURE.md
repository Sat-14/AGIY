# Multi-Agent System Architecture

## Modular Orchestration Design

### Core Principles

1. **Loose Coupling**: Each agent is an independent microservice that can be deployed, scaled, and modified without affecting others
2. **Service Independence**: Agents communicate only via REST APIs with well-defined contracts
3. **Extensibility**: New agents can be added by simply:
   - Creating a new Flask service
   - Adding a tool function in `tools.py`
   - Updating the `all_tools` list

### Agent Communication Pattern

```
┌─────────────────────────────────────────┐
│     Sales Agent (Orchestrator)          │
│     - Maintains conversation state      │
│     - Selects appropriate tools         │
│     - Loose coupling via HTTP calls     │
└────────┬────────────────────────────────┘
         │
         │ HTTP REST API Calls
         │ (JSON Request/Response)
         │
    ┌────┴────┬────────┬────────┬────────┬────────┐
    │         │        │        │        │        │
    ▼         ▼        ▼        ▼        ▼        ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
│Recom-  ││Inven-  ││Fulfill ││Payment ││Post-   ││Loyalty │
│mend    ││tory    ││ment    ││Agent   ││Purchase││Agent   │
│5002    ││5003    ││5001    ││5005    ││5004    ││5006    │
└────────┘└────────┘└────────┘└────────┘└────────┘└────────┘
```

### How to Add a New Agent (e.g., Gift Wrapping Agent)

#### Step 1: Create the Agent Service

```python
# gift-wrapping-agent/agent.py
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/check-gift-wrapping', methods=['POST'])
def check_gift_wrapping():
    data = request.get_json()
    product_id = data.get("productId")

    return jsonify({
        "status": "success",
        "available": True,
        "options": [
            {"type": "standard", "price": 50},
            {"type": "premium", "price": 150}
        ]
    }), 200

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5007, debug=False)
```

#### Step 2: Add Tool Function

```python
# tools.py
@tool
def check_gift_wrapping(product_id: str) -> str:
    """
    Checks gift wrapping options for a product.
    """
    print(f"--- >>> CONTACTING GIFT WRAPPING AGENT <<< ---")

    url = "http://127.0.0.1:5007/check-gift-wrapping"
    payload = {"productId": product_id}

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return json.dumps(response.json())
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gift Wrapping Agent: {e}")
        return json.dumps({"status": "error"})
```

#### Step 3: Register the Tool

```python
# tools.py (at the end)
all_tools = [
    check_inventory,
    get_recommendations,
    initiate_checkout,
    reserve_in_store,
    get_applicable_offers,
    get_order_status,
    check_gift_wrapping  # <-- Add new tool here
]
```

That's it! No changes needed to:
- Main sales agent logic
- Other agents
- Database schema
- Deployment configuration

### Benefits of This Architecture

✅ **Scalability**: Each agent can scale independently based on load
✅ **Maintainability**: Changes to one agent don't affect others
✅ **Testability**: Each agent can be tested in isolation
✅ **Technology Flexibility**: Each agent can use different tech stacks
✅ **Team Autonomy**: Different teams can own different agents
✅ **Resilience**: If one agent fails, others continue working
✅ **Easy Debugging**: Clear boundaries make issues easier to trace

### API Contract Specifications

Each agent has a `.JSON` file defining its contract:
- `recommendation.JSON`
- `inventory.JSON`
- `fulfillment.JSON`
- `payment.JSON`
- `postPurchase.JSON`
- `loyalty.JSON`

These serve as documentation and can be used for:
- API validation
- Client code generation
- Integration testing
- Contract testing

### Omnichannel Session Management

The system maintains session continuity through:

1. **User Session Store**: Dictionary-based session storage (Redis in production)
2. **Conversation Memory**: LangChain's `ConversationBufferMemory` stores chat history
3. **User ID Tracking**: Persistent `current_user_id` across channels
4. **Context Preservation**: Memory is saved when user exits and restored on return

Example:
```python
# Session saved when user exits chat
user_sessions[current_user_id] = memory

# Session restored when user returns (even from different channel)
if current_user_id in user_sessions:
    memory = user_sessions[current_user_id]
```

### Edge Case Handling

#### 1. Payment Failures
- **Mock Cards**:
  - `4242` → Success
  - `1111` → Insufficient funds
  - `2222` → Expired card
  - `3333` → Network error
- **Agent Response**: Includes suggestions array for recovery
- **Sales Agent**: Gracefully handles and offers alternatives

#### 2. Out of Stock
- **Detection**: Inventory agent checks warehouse + store stock
- **Agent Response**: Returns `onlineStatus: "out_of_stock"`
- **Sales Agent**: Trained to suggest alternatives from recommendations

#### 3. Low Stock
- **Detection**: Stock < 50 units total
- **Agent Response**: Returns `onlineStatus: "low_stock"` with exact counts
- **Sales Agent**: Creates urgency ethically

#### 4. Unavailable Size/Color
- **Handling**: Inventory agent filters by attributes
- **Agent Response**: Returns empty store list if unavailable
- **Sales Agent**: Suggests similar items with available attributes

### Sales Psychology Implementation

The main sales agent prompt includes:

1. **Open-Ended Questions** - Understand customer needs
2. **Active Listening** - Reference previous interactions
3. **Complementary Suggestions** - Bundle recommendations
4. **Objection Handling** - Graceful recovery from issues
5. **Ethical Urgency** - Highlight limited stock truthfully

All implemented in the system prompt in `main.py`.

---

## Production Considerations

For production deployment:

1. Replace in-memory stores with databases (PostgreSQL, Redis)
2. Add authentication/authorization (JWT)
3. Implement rate limiting
4. Add comprehensive logging (ELK stack)
5. Use production WSGI servers (Gunicorn)
6. Containerize with Docker
7. Orchestrate with Kubernetes
8. Add API gateway for routing
9. Implement circuit breakers for resilience
10. Add monitoring and alerting
