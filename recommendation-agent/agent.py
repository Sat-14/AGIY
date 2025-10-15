import json
from flask import Flask, request, jsonify
from datetime import datetime

def analyze_user_profile(user_id):
    """
    Simulates analyzing customer profile and history.
    In production, this would query a database.
    """
    # Mock user profiles
    user_profiles = {
        "user_12345": {
            "preferences": ["casual", "denim", "blue"],
            "size": "M",
            "purchase_history": ["SKU_TSH_01", "SKU_JNS_02"],
            "browsing_history": ["jackets", "shirts", "casual wear"]
        }
    }
    return user_profiles.get(user_id, {
        "preferences": ["casual"],
        "browsing_history": ["general"]
    })

def get_seasonal_trends():
    """Get current seasonal trends"""
    month = datetime.now().month
    if month in [12, 1, 2]:
        return ["winter jackets", "hoodies", "sweaters", "warm clothing"]
    elif month in [3, 4, 5]:
        return ["light jackets", "t-shirts", "spring wear"]
    elif month in [6, 7, 8]:
        return ["summer wear", "shorts", "light clothing"]
    else:
        return ["jackets", "transitional wear", "layering pieces"]

def generate_recommendations(user_id, context, count=3):
    """
    Core recommendation logic.
    Analyzes:
    - Customer profile
    - Browsing history
    - Seasonal trends
    - Current context
    """
    print("--- RECOMMENDATION AGENT ACTION ---")
    print(f"Analyzing profile for user '{user_id}'")

    # Get user profile
    profile = analyze_user_profile(user_id)
    print(f"User preferences: {profile.get('preferences', [])}")

    # Get seasonal trends
    trends = get_seasonal_trends()
    print(f"Current seasonal trends: {trends}")

    # Mock product database
    all_products = [
        {
            "productId": "SKU_JCK_01",
            "name": "Denim Trucker Jacket",
            "category": "jackets",
            "price": 4999,
            "tags": ["casual", "denim", "blue", "classic"],
            "imageUrl": "https://example.com/img/jacket1.jpg",
            "season": ["spring", "fall"]
        },
        {
            "productId": "SKU_JCK_02",
            "name": "Classic Biker Jacket",
            "category": "jackets",
            "price": 8999,
            "tags": ["edgy", "leather", "black", "statement"],
            "imageUrl": "https://example.com/img/jacket2.jpg",
            "season": ["fall", "winter"]
        },
        {
            "productId": "SKU_JCK_03",
            "name": "Lightweight Puffer Jacket",
            "category": "jackets",
            "price": 5499,
            "tags": ["sporty", "casual", "comfortable", "blue"],
            "imageUrl": "https://example.com/img/jacket3.jpg",
            "season": ["winter", "spring"]
        },
        {
            "productId": "SKU_TSH_01",
            "name": "Classic White T-Shirt",
            "category": "t-shirts",
            "price": 1299,
            "tags": ["basic", "casual", "white", "everyday"],
            "imageUrl": "https://example.com/img/tshirt1.jpg",
            "season": ["all"]
        },
        {
            "productId": "SKU_CHN_01",
            "name": "Slim Fit Chinos",
            "category": "pants",
            "price": 3499,
            "tags": ["formal-casual", "versatile", "beige"],
            "imageUrl": "https://example.com/img/chinos1.jpg",
            "season": ["all"]
        },
        {
            "productId": "SKU_SWT_01",
            "name": "Comfort Hoodie",
            "category": "hoodies",
            "price": 2999,
            "tags": ["casual", "comfortable", "grey", "relaxed"],
            "imageUrl": "https://example.com/img/hoodie1.jpg",
            "season": ["winter", "fall"]
        }
    ]

    # Filter based on context
    context_lower = context.lower()
    filtered_products = []

    for product in all_products:
        score = 0

        # Match context keywords
        if any(tag in context_lower for tag in product["tags"]):
            score += 3
        if product["category"] in context_lower:
            score += 5

        # Match user preferences
        if any(pref in product["tags"] for pref in profile.get("preferences", [])):
            score += 2

        # Seasonal relevance
        month = datetime.now().month
        season_map = {
            (12, 1, 2): "winter",
            (3, 4, 5): "spring",
            (6, 7, 8): "summer",
            (9, 10, 11): "fall"
        }
        current_season = next((v for k, v in season_map.items() if month in k), "all")
        if current_season in product["season"] or "all" in product["season"]:
            score += 1

        if score > 0:
            filtered_products.append({"product": product, "score": score})

    # Sort by score and take top N
    filtered_products.sort(key=lambda x: x["score"], reverse=True)
    top_products = [item["product"] for item in filtered_products[:count]]

    # Format response
    recommendations = []
    for product in top_products:
        recommendations.append({
            "productId": product["productId"],
            "name": product["name"],
            "imageUrl": product["imageUrl"],
            "price": {
                "amount": product["price"],
                "currency": "INR"
            },
            "tags": product["tags"]
        })

    # Generate bundle suggestions
    bundles = []
    if any("jacket" in p["category"] for p in top_products):
        bundles.append({
            "bundleName": "Complete Casual Look",
            "products": ["SKU_JCK_01", "SKU_TSH_01", "SKU_CHN_01"],
            "discount": "15% OFF",
            "totalPrice": 8997
        })

    print(f"Generated {len(recommendations)} recommendations")

    return {
        "recommendations": recommendations,
        "bundles": bundles,
        "promotions": ["NEW_USER_20", "SEASONAL_SALE"]
    }

# Create Flask app
app = Flask(__name__)

@app.route('/get-recommendations', methods=['POST'])
def get_recommendations_endpoint():
    """API endpoint for product recommendations"""
    data = request.json

    user_id = data.get('user_id')
    context = data.get('context', 'general')
    count = data.get('count', 3)

    if not user_id:
        return jsonify({"status": "error", "message": "Missing user_id"}), 400

    try:
        result = generate_recommendations(user_id, context, count)
        return jsonify({"status": "success", **result})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5002, debug=False)
