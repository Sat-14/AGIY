import json
import sys
import os
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

# Add parent directory to path to import local_llm modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from local_llm.llm_manager import LocalLLMManager
from local_llm.m1_optimized_config import M1_8GB_CONFIGS, M1_AGENT_PROMPTS

# Initialize local LLM for post-purchase agent (TinyLlama - good for customer support)
llm_manager = LocalLLMManager(M1_8GB_CONFIGS["post_purchase"])

app = Flask(__name__)

# Mock database of orders
ORDERS_DB = {
    "ORD-12345": {
        "orderId": "ORD-12345",
        "status": "out_for_delivery",
        "statusDescription": "Your order is out for delivery and should arrive today.",
        "estimatedDelivery": (datetime.now() + timedelta(days=0)).strftime("%Y-%m-%d"),
        "trackingLink": "https://track.abfrl.com/ORD-12345",
        "items": ["Denim Trucker Jacket", "Cotton T-Shirt"]
    },
    "ORD-67890": {
        "orderId": "ORD-67890",
        "status": "in_transit",
        "statusDescription": "Your package is currently in transit and expected tomorrow.",
        "estimatedDelivery": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "trackingLink": "https://track.abfrl.com/ORD-67890",
        "items": ["Classic Biker Jacket"]
    },
    "ORD-A1465": {
        "orderId": "ORD-A1465",
        "status": "dispatched",
        "statusDescription": "Your order has been dispatched and will reach you soon.",
        "estimatedDelivery": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
        "trackingLink": "https://track.abfrl.com/ORD-A1465",
        "items": ["Lightweight Puffer Jacket"]
    }
}

def generate_support_response_with_llm(order_id, query_type, order_data):
    """
    Use LLM to generate empathetic customer support responses.
    TinyLlama is good for conversational customer support.
    """
    prompt = M1_AGENT_PROMPTS["post_purchase"].format(
        order_id=order_id,
        query=query_type
    )

    context = f"""Customer Support Request:
Order ID: {order_id}
Status: {order_data.get('status', 'unknown')}
Query Type: {query_type}
Items: {', '.join(order_data.get('items', []))}
Estimated Delivery: {order_data.get('estimatedDelivery', 'N/A')}

Provide helpful and empathetic response."""

    try:
        llm_response = llm_manager.generate_response(prompt, context)
        print(f"LLM Support Response: {llm_response}")

        # Try to parse LLM response
        try:
            llm_output = json.loads(llm_response)
            if "message" in llm_output:
                return llm_output
        except json.JSONDecodeError:
            # LLM returned text, use as message
            return {"message": llm_response.strip(), "llmGenerated": True}

    except Exception as e:
        print(f"LLM error: {e}, using fallback")

    return None

@app.route('/get-order-status', methods=['POST'])
def get_order_status():
    """
    Retrieves the current status and tracking details for an order.
    Enhanced with LLM-generated empathetic responses.
    Endpoint: POST /get-order-status
    """
    data = request.get_json()

    # Validate required fields
    order_id = data.get("orderId") or data.get("order_id")
    user_id = data.get("userId") or data.get("user_id")

    if not order_id or not user_id:
        return jsonify({
            "status": "error",
            "message": "Missing required fields: orderId and userId are required."
        }), 400

    # Look up order
    order = ORDERS_DB.get(order_id)

    if not order:
        return jsonify({
            "status": "not_found",
            "message": f"No order found with ID {order_id}. Please check your order ID and try again."
        }), 404

    # Get LLM-enhanced support message
    llm_support = generate_support_response_with_llm(order_id, "status_check", order)

    response = {
        "status": "success",
        "orderId": order["orderId"],
        "orderStatus": order["status"],
        "statusDescription": order["statusDescription"],
        "estimatedDelivery": order["estimatedDelivery"],
        "trackingLink": order["trackingLink"],
        "items": order["items"],
        "llmEnhanced": True
    }

    # Add LLM-generated message if available
    if llm_support and "message" in llm_support:
        response["supportMessage"] = llm_support["message"]

    # Collect feedback
    llm_manager.collect_feedback(
        prompt=f"order_status_{order_id}",
        response=json.dumps(response),
        rating=5,
        metadata={"order_id": order_id, "user_id": user_id}
    )

    return jsonify(response), 200

@app.route('/initiate-return', methods=['POST'])
def initiate_return():
    """
    Initiates a return or exchange for an item.
    Enhanced with LLM-generated empathetic responses.
    Endpoint: POST /initiate-return
    """
    data = request.get_json()

    order_id = data.get("orderId") or data.get("order_id")
    user_id = data.get("userId") or data.get("user_id")
    item_description = data.get("itemDescription", "")
    reason = data.get("reason", "Not specified")

    if not order_id or not user_id:
        return jsonify({
            "status": "error",
            "message": "Missing required fields: orderId and userId are required."
        }), 400

    # Check if order exists
    order = ORDERS_DB.get(order_id)
    if not order:
        return jsonify({
            "status": "error",
            "message": f"Order {order_id} not found. Cannot initiate return."
        }), 404

    # Generate return ID
    return_id = f"RET-{order_id[-5:]}-{datetime.now().strftime('%H%M%S')}"

    # Get LLM-enhanced support response
    llm_support = generate_support_response_with_llm(
        order_id,
        f"return_request: {item_description} (Reason: {reason})",
        order
    )

    pickup_estimate = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")

    response = {
        "status": "success",
        "returnId": return_id,
        "orderId": order_id,
        "message": f"Return initiated for '{item_description}' from order {order_id}. Reason: {reason}. A pickup will be scheduled within 2-3 business days.",
        "pickupEstimate": pickup_estimate,
        "llmEnhanced": True
    }

    # Add LLM-generated empathetic message
    if llm_support and "message" in llm_support:
        response["supportMessage"] = llm_support["message"]

    # Collect feedback
    llm_manager.collect_feedback(
        prompt=f"return_{return_id}",
        response=json.dumps(response),
        rating=4,  # Returns are slightly less positive
        metadata={
            "order_id": order_id,
            "user_id": user_id,
            "reason": reason
        }
    )

    return jsonify(response), 200

@app.route('/track-order', methods=['POST'])
def track_order():
    """
    Provides detailed tracking information with LLM-enhanced updates.
    Endpoint: POST /track-order
    """
    data = request.get_json()

    order_id = data.get("orderId") or data.get("order_id")
    user_id = data.get("userId") or data.get("user_id")

    if not order_id or not user_id:
        return jsonify({
            "status": "error",
            "message": "Missing required fields: orderId and userId are required."
        }), 400

    # Look up order
    order = ORDERS_DB.get(order_id)
    if not order:
        return jsonify({
            "status": "not_found",
            "message": f"Order {order_id} not found."
        }), 404

    # Generate tracking updates with LLM
    llm_support = generate_support_response_with_llm(order_id, "detailed_tracking", order)

    # Mock tracking timeline
    tracking_timeline = [
        {"status": "order_placed", "date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"), "description": "Order confirmed"},
        {"status": "packed", "date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"), "description": "Package prepared"},
        {"status": "dispatched", "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"), "description": "Shipped from warehouse"},
        {"status": order["status"], "date": datetime.now().strftime("%Y-%m-%d"), "description": order["statusDescription"]},
    ]

    response = {
        "status": "success",
        "orderId": order_id,
        "currentStatus": order["status"],
        "trackingTimeline": tracking_timeline,
        "estimatedDelivery": order["estimatedDelivery"],
        "trackingLink": order["trackingLink"],
        "llmEnhanced": True
    }

    if llm_support and "message" in llm_support:
        response["trackingInsights"] = llm_support["message"]

    return jsonify(response), 200

@app.route('/feedback', methods=['POST'])
def feedback_endpoint():
    """Collect feedback for LLM improvement"""
    data = request.json

    llm_manager.collect_feedback(
        prompt=f"post_purchase_{data.get('orderId')}",
        response=data.get('action', 'query'),
        rating=data.get('rating', 3),
        metadata=data
    )

    return jsonify({
        "status": "success",
        "message": "Feedback collected for continuous improvement"
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "agent": "post_purchase",
        "llm_model": M1_8GB_CONFIGS["post_purchase"].model_name,
        "memory_limit_mb": M1_8GB_CONFIGS["post_purchase"].max_memory_mb
    })

if __name__ == '__main__':
    print("\n" + "="*70)
    print("Post-Purchase Support Agent with Local LLM (TinyLlama 1.1B)")
    print("="*70)
    print(f"Model: {M1_8GB_CONFIGS['post_purchase'].model_name}")
    print(f"Memory Limit: {M1_8GB_CONFIGS['post_purchase'].max_memory_mb} MB")
    print(f"Quantization: {M1_8GB_CONFIGS['post_purchase'].quantization}")
    print(f"Specialization: Customer support & empathetic responses")
    print(f"Continuous Learning: Enabled")
    print("="*70 + "\n")

    # Load the model
    print("Loading LLM model...")
    llm_manager.load_model()
    print("Model loaded successfully!\n")

    print("--- Post-Purchase Support Agent (Flask API) Starting on Port 5004 ---")
    app.run(host='127.0.0.1', port=5004, debug=False)
