import json
from flask import Flask, request, jsonify

def reserve_item_in_store(user_id, product_id, store_id):
    """
    Core logic for reserving an item.
    In a real system, this function would:
    1. Connect to the store's inventory database.
    2. Place a temporary hold on the item for the user.
    3. Generate a unique reservation ID.
    4. Send an email/notification to the store staff.
    """
    print("--- FULFILLMENT AGENT ACTION ---")
    print(f"Received request to reserve product '{product_id}' at store '{store_id}' for user '{user_id}'.")
    
    # For our prototype, we'll just simulate success.
    reservation_id = f"RES-{product_id[:4]}-{store_id[:3]}-{user_id[-4:]}"
    print(f"Successfully created reservation: {reservation_id}")
    
    response_data = {
        "status": "success",
        "reservationId": reservation_id,
        "confirmationMessage": "Your item has been reserved for 24 hours."
    }
    
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
        
    # Call our core logic function
    result = reserve_item_in_store(user_id, product_id, store_id)
    
    # Send the result back to the Sales Agent
    return jsonify(result)

# This makes the script runnable
if __name__ == '__main__':
    # Runs the web server on http://127.0.0.1:5001
    # We use port 5001 so it doesn't conflict with other potential services.
    app.run(port=5001, debug=True)
