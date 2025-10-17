import json
import sys
import os
from flask import Flask, request, jsonify
from datetime import datetime
import random
import string

# Add parent directory to path to import local_llm modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from local_llm.llm_manager import LocalLLMManager
from local_llm.m1_optimized_config import M1_8GB_CONFIGS, M1_AGENT_PROMPTS

# Initialize local LLM for payment agent (StableLM - reliable for factual tasks)
llm_manager = LocalLLMManager(M1_8GB_CONFIGS["payment"])

app = Flask(__name__)

# Mock transaction database
TRANSACTIONS_DB = {}

def generate_transaction_id():
    """Generate a unique transaction ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = ''.join(random.choices(string.digits, k=4))
    return f"TXN-{timestamp}-{random_suffix}"

def validate_payment_with_llm(transaction_id, payment_method, payment_details):
    """
    Use LLM to provide intelligent payment failure suggestions.
    StableLM is reliable for factual reasoning.
    """
    prompt = M1_AGENT_PROMPTS["payment"].format(
        transaction_id=transaction_id,
        amount=TRANSACTIONS_DB.get(transaction_id, {}).get("amount", 0),
        payment_method=payment_method
    )

    context = f"""Payment Processing:
Transaction: {transaction_id}
Method: {payment_method}
Details: {json.dumps(payment_details)}

Analyze and provide actionable suggestions if failed."""

    try:
        llm_response = llm_manager.generate_response(prompt, context)
        print(f"LLM Payment Analysis: {llm_response}")

        # Try to parse LLM suggestions
        try:
            llm_output = json.loads(llm_response)
            if "suggestions" in llm_output:
                return llm_output["suggestions"]
        except json.JSONDecodeError:
            pass

    except Exception as e:
        print(f"LLM error: {e}, using fallback logic")

    return []

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
        "message": f"Payment session created. Please proceed to complete the payment of {currency} {total_amount}.",
        "llmEnhanced": True
    }), 200

@app.route('/process-payment', methods=['POST'])
def process_payment():
    """
    Processes a payment transaction with LLM-enhanced failure handling.
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

    # Simulate payment processing with multiple edge cases
    if payment_method.lower() == "credit_card":
        card_number = payment_details.get("cardNumber", "")

        if "1111" in card_number:  # Mock failing card - insufficient funds
            transaction["status"] = "failed"
            transaction["failureReason"] = "insufficient_funds"

            # Get LLM suggestions
            llm_suggestions = validate_payment_with_llm(transaction_id, payment_method, payment_details)

            return jsonify({
                "status": "failed",
                "transactionId": transaction_id,
                "failureReason": "insufficient_funds",
                "message": "Transaction Failed: Your card was declined due to insufficient funds.",
                "suggestions": llm_suggestions or [
                    "Try a different payment method",
                    "Use UPI payment",
                    "Redeem loyalty points to reduce amount",
                    "Apply available coupons"
                ],
                "llmEnhanced": True
            }), 200

        elif "2222" in card_number:  # Mock failing card - expired card
            transaction["status"] = "failed"
            transaction["failureReason"] = "card_expired"

            llm_suggestions = validate_payment_with_llm(transaction_id, payment_method, payment_details)

            return jsonify({
                "status": "failed",
                "transactionId": transaction_id,
                "failureReason": "card_expired",
                "message": "Transaction Failed: Your card has expired.",
                "suggestions": llm_suggestions or [
                    "Update your card details",
                    "Try a different card",
                    "Use UPI or other payment methods"
                ],
                "llmEnhanced": True
            }), 200

        elif "3333" in card_number:  # Mock failing card - network error
            transaction["status"] = "failed"
            transaction["failureReason"] = "network_error"

            llm_suggestions = validate_payment_with_llm(transaction_id, payment_method, payment_details)

            return jsonify({
                "status": "failed",
                "transactionId": transaction_id,
                "failureReason": "network_error",
                "message": "Transaction Failed: Network connection error. Please try again.",
                "suggestions": llm_suggestions or [
                    "Retry the payment",
                    "Check your internet connection",
                    "Try a different payment method"
                ],
                "llmEnhanced": True
            }), 200

        elif "4242" in card_number:  # Mock successful card
            transaction["status"] = "completed"
            transaction["completedAt"] = datetime.now().isoformat()

            # Collect positive feedback
            llm_manager.collect_feedback(
                prompt=f"payment_{transaction_id}",
                response=json.dumps({"status": "success"}),
                rating=5,
                metadata={"transaction_id": transaction_id, "method": payment_method}
            )

            return jsonify({
                "status": "success",
                "transactionId": transaction_id,
                "message": f"Payment of {transaction['currency']} {transaction['amount']} processed successfully.",
                "paymentMethod": payment_method,
                "llmEnhanced": True
            }), 200
        else:
            llm_suggestions = validate_payment_with_llm(transaction_id, payment_method, payment_details)

            return jsonify({
                "status": "failed",
                "transactionId": transaction_id,
                "failureReason": "invalid_card",
                "message": "Invalid card details provided.",
                "suggestions": llm_suggestions or [
                    "Check your card number",
                    "Verify card details are correct",
                    "Try a different payment method"
                ],
                "llmEnhanced": True
            }), 200

    elif payment_method.lower() == "upi":
        upi_id = payment_details.get("upiId", "")
        if "@" in upi_id:
            transaction["status"] = "completed"
            transaction["completedAt"] = datetime.now().isoformat()

            # Collect positive feedback
            llm_manager.collect_feedback(
                prompt=f"payment_{transaction_id}",
                response=json.dumps({"status": "success"}),
                rating=5,
                metadata={"transaction_id": transaction_id, "method": payment_method}
            )

            return jsonify({
                "status": "success",
                "transactionId": transaction_id,
                "message": f"Payment of {transaction['currency']} {transaction['amount']} via UPI completed successfully.",
                "paymentMethod": payment_method,
                "llmEnhanced": True
            }), 200
        else:
            return jsonify({
                "status": "failed",
                "transactionId": transaction_id,
                "message": "Invalid UPI ID.",
                "llmEnhanced": True
            }), 200

    return jsonify({
        "status": "failed",
        "message": f"Unsupported payment method: {payment_method}",
        "llmEnhanced": True
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
        "completedAt": transaction.get("completedAt"),
        "llmEnhanced": True
    }), 200

@app.route('/feedback', methods=['POST'])
def feedback_endpoint():
    """Collect feedback for LLM improvement"""
    data = request.json

    llm_manager.collect_feedback(
        prompt=f"payment_{data.get('transactionId')}",
        response=data.get('paymentStatus', 'unknown'),
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
        "agent": "payment",
        "llm_model": M1_8GB_CONFIGS["payment"].model_name,
        "memory_limit_mb": M1_8GB_CONFIGS["payment"].max_memory_mb
    })

if __name__ == '__main__':
    print("\n" + "="*70)
    print("Payment Agent with Local LLM (StableLM 1.6B)")
    print("="*70)
    print(f"Model: {M1_8GB_CONFIGS['payment'].model_name}")
    print(f"Memory Limit: {M1_8GB_CONFIGS['payment'].max_memory_mb} MB")
    print(f"Quantization: {M1_8GB_CONFIGS['payment'].quantization}")
    print(f"Specialization: Factual reasoning & transaction processing")
    print(f"Continuous Learning: Enabled")
    print("="*70 + "\n")

    # Load the model
    print("Loading LLM model...")
    llm_manager.load_model()
    print("Model loaded successfully!\n")

    print("--- Payment Agent (Flask API) Starting on Port 5005 ---")
    app.run(host='127.0.0.1', port=5005, debug=False)
