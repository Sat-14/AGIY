from flask import Flask, request, jsonify
from datetime import datetime, timedelta

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

@app.route('/get-order-status', methods=['POST'])
def get_order_status():
    """
    Retrieves the current status and tracking details for an order.
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

    # Return order details
    return jsonify({
        "status": "success",
        "orderId": order["orderId"],
        "orderStatus": order["status"],
        "statusDescription": order["statusDescription"],
        "estimatedDelivery": order["estimatedDelivery"],
        "trackingLink": order["trackingLink"],
        "items": order["items"]
    }), 200

@app.route('/initiate-return', methods=['POST'])
def initiate_return():
    """
    Initiates a return or exchange for an item.
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

    return jsonify({
        "status": "success",
        "returnId": return_id,
        "orderId": order_id,
        "message": f"Return initiated for '{item_description}' from order {order_id}. Reason: {reason}. A pickup will be scheduled within 2-3 business days.",
        "pickupEstimate": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    }), 200

if __name__ == '__main__':
    print("\n--- Post-Purchase Support Agent (Flask API) Starting on Port 5004 ---")
    app.run(host='127.0.0.1', port=5004, debug=False)
