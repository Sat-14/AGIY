import json
from langchain.tools import tool

@tool
def check_inventory(product_id: str, attributes: dict, location: str) -> str:
    """
    Checks the inventory for a given product ID, its attributes (like size and color), and a location.
    Returns the stock status and store availability.
    """
    print(f"--- Calling Inventory Agent ---")
    print(f"Checking stock for {product_id} with attributes {attributes} in {location}")

    # Mock data mimicking a real API response
    mock_inventory = {
        "productId": product_id,
        "onlineStatus": "in_stock",
        "stockLevel": 15,
        "availableStores": [
            {"storeName": "Select Citywalk", "stockLevel": 5},
            {"storeName": "DLF Promenade", "stockLevel": 2},
        ]
    }
    return json.dumps(mock_inventory)

@tool
def get_recommendations(user_id: str, context: str) -> str:
    """
    Provides product recommendations based on a user ID and their current context (e.g., 'casual blue jacket for women').
    Use this tool to find products for the user.
    """
    print(f"--- Calling Recommendation Agent ---")
    print(f"Getting recommendations for user {user_id} in context: {context}")

    # Mock data mimicking a real API response
    if "jacket" in context.lower():
        mock_products = [
            {"productId": "SKU_JCK_01", "name": "Denim Trucker Jacket", "price": 4999},
            {"productId": "SKU_JCK_02", "name": "Classic Biker Jacket", "price": 8999},
            {"productId": "SKU_JCK_03", "name": "Lightweight Puffer Jacket", "price": 5499},
        ]
        return json.dumps(mock_products)
    else:
        # Return a generic response if the context is not a jacket
        mock_products = [
            {"productId": "SKU_GEN_01", "name": "Classic White T-Shirt", "price": 1299},
            {"productId": "SKU_GEN_02", "name": "Slim Fit Chinos", "price": 3499},
        ]
        return json.dumps(mock_products)

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
    Reserves an item in a physical store for a user.
    """
    print(f"--- Calling Fulfillment Agent ---")
    print(f"Reserving product {product_id} at store {store_id} for user {user_id}")
    return json.dumps({"status": "success", "reservationId": "RES12345"})

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

# Combine all tools into a single list
all_tools = [
    check_inventory,
    get_recommendations,
    initiate_checkout,
    reserve_in_store,
    get_applicable_offers,
    get_order_status,
]