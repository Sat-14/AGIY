import json
import sys
import os
from flask import Flask, request, jsonify

# Add parent directory to path to import local_llm modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from local_llm.llm_manager import LocalLLMManager
from local_llm.m1_optimized_config import M1_8GB_CONFIGS, M1_AGENT_PROMPTS

# Initialize local LLM for fulfillment agent
llm_manager = LocalLLMManager(M1_8GB_CONFIGS["fulfillment"])

def reserve_item_in_store_with_llm(user_id, product_id, store_id):
    """
    Core logic for reserving an item with LLM validation.
    Uses lightweight Qwen 1.8B for structured decision-making.
    """
    print("--- FULFILLMENT AGENT ACTION (Local LLM) ---")
    print(f"Received request to reserve product '{product_id}' at store '{store_id}' for user '{user_id}'.")

    # Use LLM to validate and generate reservation details
    prompt = M1_AGENT_PROMPTS["fulfillment"].format(
        product_id=product_id,
        store_id=store_id,
        user_id=user_id
    )

    context = f"""Store Inventory System:
- Product: {product_id}
- Store: {store_id}
- User: {user_id}
- Action: Create 24-hour reservation
- System Status: Online

Validate inputs and generate confirmation."""

    try:
        # Get LLM response for validation
        llm_response = llm_manager.generate_response(prompt, context)
        print(f"LLM Validation: {llm_response}")

        # Parse LLM response (expecting JSON)
        try:
            llm_output = json.loads(llm_response)
            if llm_output.get("status") == "error":
                return llm_output
        except json.JSONDecodeError:
            # LLM didn't return JSON, continue with default logic
            pass

    except Exception as e:
        print(f"LLM processing error: {e}, falling back to standard logic")

    # Generate reservation ID
    reservation_id = f"RES-{product_id[:4]}-{store_id[:3]}-{user_id[-4:]}"
    print(f"Successfully created reservation: {reservation_id}")

    response_data = {
        "status": "success",
        "reservationId": reservation_id,
        "confirmationMessage": "Your item has been reserved for 24 hours.",
        "llmEnhanced": True
    }

    # Collect feedback for continuous improvement
    llm_manager.collect_feedback(
        prompt=prompt,
        response=json.dumps(response_data),
        rating=5,  # Auto-rate successful reservations
        metadata={
            "user_id": user_id,
            "product_id": product_id,
            "store_id": store_id
        }
    )

    return response_data

# Create the Flask application
app = Flask(__name__)

# Define the API endpoint for reserving an item
@app.route('/reserve-in-store', methods=['POST'])
def reserve_in_store_endpoint():
    # Get the data sent by the Sales Agent
    data = request.json

    # Extract the required information
    user_id = data.get('user_id')
    product_id = data.get('product_id')
    store_id = data.get('store_id')

    # A little validation
    if not all([user_id, product_id, store_id]):
        return jsonify({"status": "error", "message": "Missing required data"}), 400

    # Call our core logic function with LLM
    result = reserve_item_in_store_with_llm(user_id, product_id, store_id)

    # Send the result back to the Sales Agent
    return jsonify(result)

@app.route('/feedback', methods=['POST'])
def feedback_endpoint():
    """
    Endpoint for collecting feedback to improve the LLM.
    POST /feedback
    {
        "user_id": "user_123",
        "reservation_id": "RES-XXX",
        "rating": 1-5,
        "feedback": "optional text"
    }
    """
    data = request.json

    # Collect feedback for model improvement
    llm_manager.collect_feedback(
        prompt=f"reservation_{data.get('reservation_id')}",
        response=data.get('reservation_id'),
        rating=data.get('rating', 3),
        metadata={
            "user_id": data.get('user_id'),
            "feedback_text": data.get('feedback', '')
        }
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
        "agent": "fulfillment",
        "llm_model": M1_8GB_CONFIGS["fulfillment"].model_name,
        "memory_limit_mb": M1_8GB_CONFIGS["fulfillment"].max_memory_mb
    })

# This makes the script runnable
if __name__ == '__main__':
    print("\n" + "="*70)
    print("Fulfillment Agent with Local LLM (Qwen 1.8B)")
    print("="*70)
    print(f"Model: {M1_8GB_CONFIGS['fulfillment'].model_name}")
    print(f"Memory Limit: {M1_8GB_CONFIGS['fulfillment'].max_memory_mb} MB")
    print(f"Quantization: {M1_8GB_CONFIGS['fulfillment'].quantization}")
    print(f"Continuous Learning: Enabled")
    print("="*70 + "\n")

    # Load the model
    print("Loading LLM model...")
    llm_manager.load_model()
    print("Model loaded successfully!\n")

    # Runs the web server on http://127.0.0.1:5001
    app.run(port=5001, debug=False)
