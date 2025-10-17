"""
Recommendation Agent with Local LLM (M1/RTX 3060 optimized)
Uses TinyLlama 1.1B with continuous improvement via QLoRA
"""

import json
import sys
import os
from flask import Flask, request, jsonify
from datetime import datetime
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongodb_config import get_db_manager
from monitoring.tracing import TracingManager
from monitoring.metrics import MetricsManager
from monitoring.logging_config import StructuredLogger, log_api_request, log_api_response

# Local LLM imports
try:
    from local_llm.llm_manager import create_llm_manager
    USE_LOCAL_LLM = True
except ImportError:
    print("⚠️  Local LLM not available. Install: pip install transformers peft bitsandbytes")
    USE_LOCAL_LLM = False

# Initialize monitoring
tracing = TracingManager("recommendation-agent-llm", "1.0.0")
metrics = MetricsManager("recommendation-agent-llm")
logging_config = StructuredLogger("recommendation-agent-llm")
logger = logging_config.get_logger()

# Initialize MongoDB
db_manager = get_db_manager()
user_profiles_collection = db_manager.get_collection("user_profiles")
inventory_collection = db_manager.get_collection("inventory")

# Initialize Local LLM
llm_manager = None
if USE_LOCAL_LLM:
    try:
        # Try Ollama first (easier on M1)
        llm_manager = create_llm_manager("recommendation", use_ollama=True)
        logger.info("✅ Using Ollama for recommendations")
    except:
        try:
            # Fallback to HuggingFace
            llm_manager = create_llm_manager("recommendation", use_ollama=False)
            logger.info("✅ Using HuggingFace for recommendations")
        except Exception as e:
            logger.error(f"❌ Failed to load local LLM: {e}")
            llm_manager = None

# Create Flask app
app = Flask(__name__)
tracing.instrument_flask_app(app)
metrics.create_metrics_endpoint(app)


def get_user_profile(user_id: str) -> dict:
    """Fetch user profile from MongoDB"""
    try:
        profile = user_profiles_collection.find_one({"user_id": user_id})
        if profile:
            return {
                "preferences": profile.get("preferences", ["casual"]),
                "size": profile.get("size", "M"),
                "purchase_history": profile.get("purchase_history", []),
                "browsing_history": profile.get("browsing_history", [])
            }
    except:
        pass

    return {"preferences": ["casual"], "browsing_history": ["general"]}


def get_products_from_db() -> list:
    """Fetch products from MongoDB"""
    try:
        products = list(inventory_collection.find(
            {},
            {"_id": 0, "product_id": 1, "name": 1, "category": 1, "price": 1, "tags": 1}
        ))
        if products:
            return products
    except:
        pass

    # Fallback mock data
    return [
        {
            "product_id": "SKU_JCK_01",
            "name": "Denim Trucker Jacket",
            "category": "jackets",
            "price": 4999,
            "tags": ["casual", "denim", "blue"]
        },
        {
            "product_id": "SKU_TSH_01",
            "name": "Cotton T-Shirt",
            "category": "t-shirts",
            "price": 1299,
            "tags": ["casual", "basic", "white"]
        },
        {
            "product_id": "SKU_JCK_02",
            "name": "Leather Jacket",
            "category": "jackets",
            "price": 8999,
            "tags": ["formal", "leather", "black"]
        }
    ]


def generate_recommendations_with_llm(user_id: str, context: str, count: int = 3):
    """Generate recommendations using local LLM"""
    logger.info(f"Generating LLM-based recommendations for {user_id}")

    # Get user profile and products
    profile = get_user_profile(user_id)
    products = get_products_from_db()

    # Prepare context for LLM
    llm_context = {
        "context": context,
        "preferences": ", ".join(profile["preferences"]),
        "products": [
            f"{p['product_id']}: {p['name']} ({', '.join(p['tags'])})"
            for p in products[:10]  # Limit context size
        ]
    }

    if llm_manager:
        try:
            # Generate recommendations using LLM
            prompt = f"""Given customer preferences: {llm_context['preferences']}
Context: {context}

Available products:
{chr(10).join(llm_context['products'])}

Recommend {count} best matching products. Output JSON:
{{"recommendations": [{{"product_id": "SKU_X", "reason": "..."}}]}}"""

            llm_response = llm_manager.generate_response(prompt, llm_context)

            logger.info(f"LLM Response: {llm_response}")

            # Parse LLM response
            try:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    llm_recs = json.loads(json_match.group())
                    recommended_ids = [r["product_id"] for r in llm_recs.get("recommendations", [])]
                else:
                    # Fallback to pattern matching
                    recommended_ids = [p["product_id"] for p in products[:count]]
            except:
                recommended_ids = [p["product_id"] for p in products[:count]]

            # Get full product details
            recommendations = []
            for product in products:
                if product["product_id"] in recommended_ids:
                    recommendations.append({
                        "productId": product["product_id"],
                        "name": product["name"],
                        "imageUrl": f"https://example.com/img/{product['product_id']}.jpg",
                        "price": {
                            "amount": product["price"],
                            "currency": "INR"
                        },
                        "tags": product["tags"],
                        "llm_generated": True
                    })

            # Collect feedback for LLM improvement
            if hasattr(llm_manager, 'collect_feedback'):
                llm_manager.collect_feedback(
                    prompt=prompt,
                    response=llm_response,
                    rating=None,  # Will be updated based on user actions
                    metadata={"user_id": user_id, "context": context}
                )

            return {
                "recommendations": recommendations[:count],
                "bundles": [],
                "promotions": ["LLM_POWERED"],
                "llm_used": True
            }

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Fallback to rule-based

    # Fallback: Rule-based recommendations
    recommendations = []
    for product in products[:count]:
        recommendations.append({
            "productId": product["product_id"],
            "name": product["name"],
            "imageUrl": f"https://example.com/img/{product['product_id']}.jpg",
            "price": {
                "amount": product["price"],
                "currency": "INR"
            },
            "tags": product["tags"],
            "llm_generated": False
        })

    return {
        "recommendations": recommendations,
        "bundles": [],
        "promotions": ["RULE_BASED"],
        "llm_used": False
    }


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
            return jsonify({"status": "error", "message": "Missing user_id"}), 400

        # Generate recommendations
        result = generate_recommendations_with_llm(user_id, context, count)

        duration = time.time() - start_time
        log_api_response(logger, "POST", "/get-recommendations", 200, duration)
        metrics.record_request("POST", "/get-recommendations", 200, duration)

        return jsonify({"status": "success", **result})

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Error: {e}")
        metrics.record_error(type(e).__name__)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/feedback', methods=['POST'])
def feedback_endpoint():
    """Collect feedback for LLM improvement"""
    try:
        data = request.json
        user_id = data.get('user_id')
        recommendation_id = data.get('recommendation_id')
        rating = data.get('rating')  # 1-5
        action = data.get('action')  # clicked, purchased, ignored

        if llm_manager and hasattr(llm_manager, 'collect_feedback'):
            llm_manager.collect_feedback(
                prompt=f"user_{user_id}_rec",
                response=recommendation_id,
                rating=rating,
                metadata={"action": action, "user_id": user_id}
            )

        logger.info(f"Feedback collected: {user_id} rated {recommendation_id} as {rating}")

        return jsonify({"status": "success", "message": "Feedback recorded"})

    except Exception as e:
        logger.error(f"Feedback error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/model-stats', methods=['GET'])
def model_stats_endpoint():
    """Get LLM model statistics"""
    try:
        if llm_manager and hasattr(llm_manager, 'get_model_stats'):
            stats = llm_manager.get_model_stats()
            return jsonify({"status": "success", **stats})
        else:
            return jsonify({
                "status": "success",
                "llm_available": False,
                "message": "No local LLM configured"
            })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    logger.info("🚀 Starting Recommendation Agent with Local LLM on port 5002")
    if llm_manager:
        logger.info("✅ Local LLM loaded successfully")
    else:
        logger.warning("⚠️  Running in fallback mode (rule-based)")

    app.run(port=5002, debug=False)
