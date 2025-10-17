import json
import sys
import os
from flask import Flask, request, jsonify
from datetime import datetime
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongodb_config import get_db_manager
from monitoring.tracing import TracingManager, trace_function
from monitoring.metrics import MetricsManager
from monitoring.logging_config import (
    StructuredLogger,
    log_api_request,
    log_api_response,
    log_db_operation,
    log_error
)

# Initialize monitoring
tracing = TracingManager("recommendation-agent", "1.0.0")
metrics = MetricsManager("recommendation-agent")
logging_config = StructuredLogger("recommendation-agent")
logger = logging_config.get_logger()

# Initialize MongoDB
db_manager = get_db_manager()
user_profiles_collection = db_manager.get_collection("user_profiles")
inventory_collection = db_manager.get_collection("inventory")
recommendations_cache = db_manager.get_collection("recommendations_cache")

# Create Flask app
app = Flask(__name__)

# Instrument Flask app for tracing
tracing.instrument_flask_app(app)
metrics.create_metrics_endpoint(app)


@trace_function
def analyze_user_profile(user_id):
    """Fetch user profile from MongoDB"""
    try:
        start_time = time.time()

        profile = user_profiles_collection.find_one({"user_id": user_id})

        duration = time.time() - start_time
        log_db_operation(logger, "user_profiles", "find_one", user_id, duration)
        metrics.record_db_operation("user_profiles", "find", "success", duration)

        if profile:
            return {
                "preferences": profile.get("preferences", ["casual"]),
                "size": profile.get("size", "M"),
                "purchase_history": profile.get("purchase_history", []),
                "browsing_history": profile.get("browsing_history", [])
            }

        # Return default profile if not found
        logger.warning(f"User profile not found for {user_id}, using defaults")
        return {
            "preferences": ["casual"],
            "browsing_history": ["general"]
        }

    except Exception as e:
        log_error(logger, e, {"operation": "analyze_user_profile"})
        metrics.record_error("user_profile_fetch_error")
        return {"preferences": ["casual"], "browsing_history": ["general"]}


@trace_function
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


@trace_function
def get_products_from_db():
    """Fetch products from MongoDB inventory"""
    try:
        start_time = time.time()

        products = list(inventory_collection.find(
            {},
            {"_id": 0, "product_id": 1, "name": 1, "category": 1, "price": 1, "tags": 1}
        ))

        duration = time.time() - start_time
        log_db_operation(logger, "inventory", "find", None, duration)
        metrics.record_db_operation("inventory", "find", "success", duration)

        if not products:
            # Fallback to mock data if DB is empty
            logger.warning("No products in database, using mock data")
            return get_mock_products()

        return products

    except Exception as e:
        log_error(logger, e, {"operation": "get_products_from_db"})
        metrics.record_error("product_fetch_error")
        return get_mock_products()


def get_mock_products():
    """Mock product database (fallback)"""
    return [
        {
            "product_id": "SKU_JCK_01",
            "name": "Denim Trucker Jacket",
            "category": "jackets",
            "price": 4999,
            "tags": ["casual", "denim", "blue", "classic"]
        },
        {
            "product_id": "SKU_JCK_02",
            "name": "Classic Biker Jacket",
            "category": "jackets",
            "price": 8999,
            "tags": ["edgy", "leather", "black", "statement"]
        },
        {
            "product_id": "SKU_JCK_03",
            "name": "Lightweight Puffer Jacket",
            "category": "jackets",
            "price": 5499,
            "tags": ["sporty", "casual", "comfortable", "blue"]
        },
        {
            "product_id": "SKU_TSH_01",
            "name": "Classic White T-Shirt",
            "category": "t-shirts",
            "price": 1299,
            "tags": ["basic", "casual", "white", "everyday"]
        },
        {
            "product_id": "SKU_CHN_01",
            "name": "Slim Fit Chinos",
            "category": "pants",
            "price": 3499,
            "tags": ["formal-casual", "versatile", "beige"]
        },
        {
            "product_id": "SKU_SWT_01",
            "name": "Comfort Hoodie",
            "category": "hoodies",
            "price": 2999,
            "tags": ["casual", "comfortable", "grey", "relaxed"]
        }
    ]


@trace_function
def generate_recommendations(user_id, context, count=3):
    """Core recommendation logic with MongoDB integration"""
    logger.info(f"Generating recommendations for user {user_id} with context: {context}")

    with tracing.create_span("generate_recommendations") as span:
        span.set_attribute("user_id", user_id)
        span.set_attribute("context", context)
        span.set_attribute("count", count)

        # Check cache first
        cache_key = f"{user_id}_{context}_{count}"
        cached = recommendations_cache.find_one({"cache_key": cache_key})

        if cached and (datetime.utcnow() - cached["created_at"]).seconds < 1800:  # 30 min cache
            logger.info("Returning cached recommendations")
            metrics.cache_hit_rate.labels(cache_type="recommendations").set(1.0)
            return cached["result"]

        metrics.cache_hit_rate.labels(cache_type="recommendations").set(0.0)

        # Get user profile from MongoDB
        profile = analyze_user_profile(user_id)
        logger.info(f"User preferences: {profile.get('preferences', [])}")

        # Get seasonal trends
        trends = get_seasonal_trends()
        logger.info(f"Current seasonal trends: {trends}")

        # Get products from MongoDB
        all_products = get_products_from_db()

        # Filter and score products
        context_lower = context.lower()
        filtered_products = []

        for product in all_products:
            score = 0

            # Match context keywords
            if any(tag in context_lower for tag in product.get("tags", [])):
                score += 3
            if product.get("category", "") in context_lower:
                score += 5

            # Match user preferences
            if any(pref in product.get("tags", []) for pref in profile.get("preferences", [])):
                score += 2

            # Seasonal relevance
            month = datetime.now().month
            score += 1  # Default seasonal boost

            if score > 0:
                filtered_products.append({"product": product, "score": score})

        # Sort by score and take top N
        filtered_products.sort(key=lambda x: x["score"], reverse=True)
        top_products = [item["product"] for item in filtered_products[:count]]

        # Format response
        recommendations = []
        for product in top_products:
            recommendations.append({
                "productId": product["product_id"],
                "name": product["name"],
                "imageUrl": f"https://example.com/img/{product['product_id']}.jpg",
                "price": {
                    "amount": product["price"],
                    "currency": "INR"
                },
                "tags": product.get("tags", [])
            })

        # Generate bundle suggestions
        bundles = []
        if any("jacket" in p.get("category", "") for p in top_products):
            bundles.append({
                "bundleName": "Complete Casual Look",
                "products": ["SKU_JCK_01", "SKU_TSH_01", "SKU_CHN_01"],
                "discount": "15% OFF",
                "totalPrice": 8997
            })

        result = {
            "recommendations": recommendations,
            "bundles": bundles,
            "promotions": ["NEW_USER_20", "SEASONAL_SALE"]
        }

        # Cache the result
        try:
            recommendations_cache.insert_one({
                "cache_key": cache_key,
                "user_id": user_id,
                "context": context,
                "result": result,
                "created_at": datetime.utcnow()
            })
        except:
            pass  # Cache failure shouldn't break the flow

        # Record metrics
        user_tier = profile.get("loyalty_tier", "unknown")
        metrics.recommendations_generated.labels(user_tier=user_tier).inc()

        logger.info(f"Generated {len(recommendations)} recommendations")
        return result


@app.route('/get-recommendations', methods=['POST'])
def get_recommendations_endpoint():
    """API endpoint for product recommendations"""
    start_time = time.time()

    try:
        data = request.json
        log_api_request(logger, "POST", "/get-recommendations", data)

        user_id = data.get('user_id')
        context = data.get('context', 'general')
        count = data.get('count', 3)

        if not user_id:
            response = {"status": "error", "message": "Missing user_id"}
            return jsonify(response), 400

        result = generate_recommendations(user_id, context, count)

        duration = time.time() - start_time
        log_api_response(logger, "POST", "/get-recommendations", 200, duration)
        metrics.record_request("POST", "/get-recommendations", 200, duration)

        return jsonify({"status": "success", **result})

    except Exception as e:
        duration = time.time() - start_time
        log_error(logger, e, {"endpoint": "/get-recommendations"})
        log_api_response(logger, "POST", "/get-recommendations", 500, duration)
        metrics.record_request("POST", "/get-recommendations", 500, duration)
        metrics.record_error(type(e).__name__)

        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    logger.info("Starting Recommendation Agent on port 5002")
    app.run(port=5002, debug=False)
