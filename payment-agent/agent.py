from flask import Flask, request, jsonify
from datetime import datetime
import random
import string

app = Flask(__name__)

# Mock transaction database
TRANSACTIONS_DB = {}

def generate_transaction_id():
    """Generate a unique transaction ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = ''.join(random.choices(string.digits, k=4))
    return f"TXN-{timestamp}-{random_suffix}"

@app.route('/initiate-checkout', methods=['POST'])
def initiate_checkout():
    """
    Creates a secure payment session for the user's current cart.
    Endpoint: POST /initiate-checkout
    """
    data = request.get_json()

    # Validate required fields
    user_id = data.get("userId") or data.get("user_id")
    cart_id = data.get("cartId") or data.get("cart_id")
    total_amount = data.get("totalAmount") or data.get("total_amount")
    currency = data.get("currency", "INR")

    if not user_id or not cart_id or not total_amount:
        return jsonify({
            "status": "error",
            "message": "Missing required fields: userId, cartId, and totalAmount are required."
        }), 400

    # Generate transaction ID
    transaction_id = generate_transaction_id()

    # Simulate payment gateway URL
    payment_gateway_url = f"https://payment.abfrl.com/checkout/{transaction_id}"

    # Store transaction in mock DB
    TRANSACTIONS_DB[transaction_id] = {
        "transactionId": transaction_id,
        "userId": user_id,
        "cartId": cart_id,
        "amount": total_amount,
        "currency": currency,
        "status": "initiated",
        "createdAt": datetime.now().isoformat()
    }

    return jsonify({
        "status": "success",
        "transactionId": transaction_id,
        "paymentGatewayUrl": payment_gateway_url,
        "checkoutStatus": "initiated",
        "amount": total_amount,
        "currency": currency,
        "message": f"Payment session created. Please proceed to complete the payment of {currency} {total_amount}."
    }), 200

@app.route('/process-payment', methods=['POST'])
def process_payment():
    """
    Processes a payment transaction.
    Endpoint: POST /process-payment
    """
    data = request.get_json()

    transaction_id = data.get("transactionId") or data.get("transaction_id")
    payment_method = data.get("paymentMethod") or data.get("payment_method", "credit_card")
    payment_details = data.get("paymentDetails") or data.get("payment_details", {})

    if not transaction_id:
        return jsonify({
            "status": "error",
            "message": "Missing required field: transactionId"
        }), 400

    # Check if transaction exists
    transaction = TRANSACTIONS_DB.get(transaction_id)
    if not transaction:
        return jsonify({
            "status": "error",
            "message": f"Transaction {transaction_id} not found."
        }), 404

    # Simulate payment processing
    if payment_method.lower() == "credit_card":
        card_number = payment_details.get("cardNumber", "")
        if "1111" in card_number:  # Mock failing card
            transaction["status"] = "failed"
            return jsonify({
                "status": "failed",
                "transactionId": transaction_id,
                "message": "Transaction Failed: Your card was declined due to insufficient funds."
            }), 200
        elif "4242" in card_number:  # Mock successful card
            transaction["status"] = "completed"
            transaction["completedAt"] = datetime.now().isoformat()
            return jsonify({
                "status": "success",
                "transactionId": transaction_id,
                "message": f"Payment of {transaction['currency']} {transaction['amount']} processed successfully.",
                "paymentMethod": payment_method
            }), 200
        else:
            return jsonify({
                "status": "failed",
                "transactionId": transaction_id,
                "message": "Invalid card details provided."
            }), 200

    elif payment_method.lower() == "upi":
        upi_id = payment_details.get("upiId", "")
        if "@" in upi_id:
            transaction["status"] = "completed"
            transaction["completedAt"] = datetime.now().isoformat()
            return jsonify({
                "status": "success",
                "transactionId": transaction_id,
                "message": f"Payment of {transaction['currency']} {transaction['amount']} via UPI completed successfully.",
                "paymentMethod": payment_method
            }), 200
        else:
            return jsonify({
                "status": "failed",
                "transactionId": transaction_id,
                "message": "Invalid UPI ID."
            }), 200

    return jsonify({
        "status": "failed",
        "message": f"Unsupported payment method: {payment_method}"
    }), 400

@app.route('/check-payment-status', methods=['POST'])
def check_payment_status():
    """
    Checks the status of a payment transaction.
    Endpoint: POST /check-payment-status
    """
    data = request.get_json()

    transaction_id = data.get("transactionId") or data.get("transaction_id")

    if not transaction_id:
        return jsonify({
            "status": "error",
            "message": "Missing required field: transactionId"
        }), 400

    # Look up transaction
    transaction = TRANSACTIONS_DB.get(transaction_id)

    if not transaction:
        return jsonify({
            "status": "not_found",
            "message": f"No transaction found with ID {transaction_id}."
        }), 404

    return jsonify({
        "status": "success",
        "transactionId": transaction_id,
        "paymentStatus": transaction["status"],
        "amount": transaction["amount"],
        "currency": transaction["currency"],
        "createdAt": transaction["createdAt"],
        "completedAt": transaction.get("completedAt")
    }), 200

if __name__ == '__main__':
    print("\n--- Payment Agent (Flask API) Starting on Port 5005 ---")
    app.run(host='127.0.0.1', port=5005, debug=False)