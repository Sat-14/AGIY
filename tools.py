import json
import requests
from langchain.tools import tool

@tool
def check_inventory(product_id: str, location: str, size: str = None, color: str = None) -> str:
    """
    Checks the inventory for a given product ID and location.
    Provides real-time stock across warehouses and stores with fulfillment options.
    You can also specify optional attributes like size and color.
    """
    print(f"--- >>> CONTACTING LIVE INVENTORY AGENT <<< ---")

    url = "http://127.0.0.1:5003/check-inventory"

    # Build attributes and location context
    attributes = {}
    if size:
        attributes['size'] = size
    if color:
        attributes['color'] = color

    location_context = {"city": location} if location else {}

    payload = {
        "product_id": product_id,
        "attributes": attributes,
        "location_context": location_context
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return json.dumps(response.json())

    except requests.exceptions.RequestException as e:
        print(f"Error calling Inventory Agent: {e}")
        return json.dumps({"status": "error", "message": "Could not connect to the inventory service."})

@tool
def get_recommendations(user_id: str, context: str, count: int = 3) -> str:
    """
    Provides product recommendations based on a user ID and their current context (e.g., 'casual blue jacket for women').
    Analyzes customer profile, browsing history, and seasonal trends.
    Returns personalized product suggestions, bundles, and promotions.
    Use this tool to find products for the user.
    """
    print(f"--- >>> CONTACTING LIVE RECOMMENDATION AGENT <<< ---")

    url = "http://127.0.0.1:5002/get-recommendations"
    payload = {
        "user_id": user_id,
        "context": context,
        "count": count
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return json.dumps(response.json())

    except requests.exceptions.RequestException as e:
        print(f"Error calling Recommendation Agent: {e}")
        return json.dumps({"status": "error", "message": "Could not connect to the recommendation service."})

@tool
def initiate_checkout(user_id: str, cart_id: str) -> str:
    """
    Initiates the payment process for a user's cart.
    """
    print(f"--- Calling Payment Agent ---")
    print(f"Starting checkout for user {user_id} with cart {cart_id}")
    return json.dumps({"status": "success", "paymentUrl": "https://example.com/pay"})

@tool
def reserve_in_store(user_id: str, product_id: str, store_id: str) -> str:
    """
    Reserves an item in a physical store for a user by calling the Fulfillment Agent API.
    """
    print(f"--- >>> CONTACTING LIVE FULFILLMENT AGENT <<< ---")
    
    url = "http://127.0.0.1:5001/reserve-in-store"
    payload = {
        "user_id": user_id,
        "product_id": product_id,
        "store_id": store_id
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return json.dumps(response.json())
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling Fulfillment Agent: {e}")
        return json.dumps({"status": "error", "message": "Could not connect to the fulfillment service."})

@tool
def get_applicable_offers(user_id: str, cart_id: str) -> str:
    """
    Retrieves applicable offers and loyalty points for a user's cart.
    """
    print(f"--- Calling Loyalty & Offers Agent ---")
    print(f"Fetching offers for user {user_id} and cart {cart_id}")
    return json.dumps({"offers": ["20% OFF", "FREE_SHIPPING"]})

@tool
def get_order_status(order_id: str, user_id: str) -> str:
    """
    Gets the status of a previously placed order.
    """
    print(f"--- Calling Post-Purchase Support Agent ---")
    print(f"Checking status for order {order_id} for user {user_id}")
    return json.dumps({"orderId": order_id, "status": "Shipped", "trackingLink": "https://example.com/track/123"})

all_tools = [
    check_inventory,
    get_recommendations,
    initiate_checkout,
    reserve_in_store,
    get_applicable_offers,
    get_order_status,
]

