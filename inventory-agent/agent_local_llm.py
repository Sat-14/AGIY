"""
Inventory Agent with Local LLM (M1/RTX 3060 optimized)
Uses StableLM 1.6B with continuous improvement via QLoRA
"""

import json
import sys
import os
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
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
    print("⚠️  Local LLM not available")
    USE_LOCAL_LLM = False

# Initialize monitoring
tracing = TracingManager("inventory-agent-llm", "1.0.0")
metrics = MetricsManager("inventory-agent-llm")
logging_config = StructuredLogger("inventory-agent-llm")
logger = logging_config.get_logger()

# Initialize MongoDB
db_manager = get_db_manager()
inventory_collection = db_manager.get_collection("inventory")

# Initialize Local LLM
llm_manager = None
if USE_LOCAL_LLM:
    try:
        llm_manager = create_llm_manager("inventory", use_ollama=True)
        logger.info("✅ Using Ollama for inventory")
    except:
        try:
            llm_manager = create_llm_manager("inventory", use_ollama=False)
            logger.info("✅ Using HuggingFace for inventory")
        except Exception as e:
            logger.error(f"❌ Failed to load local LLM: {e}")

# Create Flask app
app = Flask(__name__)
tracing.instrument_flask_app(app)
metrics.create_metrics_endpoint(app)


def get_inventory_from_db(product_id: str):
    """Fetch inventory from MongoDB"""
    try:
        product = inventory_collection.find_one({"product_id": product_id})
        if product:
            return product
    except:
        pass
    return None


def calculate_stock_status_with_llm(product_id: str, warehouses: list, stores: list):
    """Use LLM to analyze stock and provide intelligent recommendations"""

    total_stock = sum(w.get("stockLevel", 0) for w in warehouses)
    store_stock = sum(s.get("stockLevel", 0) for s in stores)

    if llm_manager:
        try:
            # Prepare context for LLM
            context = {
                "query": f"Analyze stock for {product_id}",
                "location": "Multiple locations",
                "data": f"Total warehouse stock: {total_stock}, Store stock: {store_stock}"
            }

            prompt = f"""Stock Analysis:
Product: {product_id}
Warehouse Stock: {total_stock} units
Store Stock: {store_stock} units
Stores: {len(stores)} locations

Determine:
1. Stock status (in_stock/low_stock/out_of_stock)
2. Urgency level (high/medium/low)
3. Recommendation

Output JSON:
{{"status": "...", "urgency": "...", "recommendation": "..."}}"""

            llm_response = llm_manager.generate_response(prompt, context)

            # Parse LLM response
            import re
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                llm_analysis = json.loads(json_match.group())

                # Collect feedback
                if hasattr(llm_manager, 'collect_feedback'):
                    llm_manager.collect_feedback(
                        prompt=prompt,
                        response=llm_response,
                        metadata={"product_id": product_id, "total_stock": total_stock}
                    )

                return {
                    "status": llm_analysis.get("status", "unknown"),
                    "urgency": llm_analysis.get("urgency", "medium"),
                    "recommendation": llm_analysis.get("recommendation", ""),
                    "llm_analyzed": True
                }

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")

    # Fallback: Rule-based
    if total_stock == 0:
        status = "out_of_stock"
        urgency = "high"
        recommendation = "Product out of stock. Consider alternatives."
    elif total_stock < 50:
        status = "low_stock"
        urgency = "high"
        recommendation = "Limited stock. Order soon!"
    else:
        status = "in_stock"
        urgency = "low"
        recommendation = "Good availability."

    return {
        "status": status,
        "urgency": urgency,
        "recommendation": recommendation,
        "llm_analyzed": False
    }


@app.route('/check-inventory', methods=['POST'])
def check_inventory_endpoint():
    """API endpoint for inventory checking with LLM"""
    start_time = time.time()

    try:
        data = request.json
        log_api_request(logger, "POST", "/check-inventory", data)

        product_id = data.get('product_id')
        attributes = data.get('attributes', {})
        location_context = data.get('location_context', {})

        if not product_id:
            return jsonify({"status": "error", "message": "Missing product_id"}), 400

        # Get inventory from DB
        product = get_inventory_from_db(product_id)

        # Mock data if not in DB
        warehouses = product.get("warehouses", []) if product else [
            {"warehouseId": "WH_NORTH", "warehouseName": "North Warehouse", "location": "Delhi", "stockLevel": 150},
            {"warehouseId": "WH_SOUTH", "warehouseName": "South Warehouse", "location": "Bangalore", "stockLevel": 80}
        ]

        stores = product.get("stores", []) if product else [
            {"storeId": "STORE_01", "storeName": "Select Citywalk", "city": "Delhi", "stockLevel": 5}
        ]

        # LLM-based stock analysis
        llm_analysis = calculate_stock_status_with_llm(product_id, warehouses, stores)

        total_stock = sum(w.get("stockLevel", 0) for w in warehouses)

        # Determine fulfillment options
        fulfillment_options = []
        if llm_analysis["status"] in ["in_stock", "low_stock"]:
            fulfillment_options.append({
                "type": "ship_to_home",
                "available": True,
                "estimatedDelivery": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
                "urgency": llm_analysis["urgency"]
            })

        if any(s.get("stockLevel", 0) > 0 for s in stores):
            fulfillment_options.append({
                "type": "click_and_collect",
                "available": True,
                "message": llm_analysis["recommendation"]
            })

        result = {
            "productId": product_id,
            "onlineStatus": llm_analysis["status"],
            "onlineStockLevel": total_stock,
            "warehouses": warehouses,
            "availableStores": stores,
            "fulfillmentOptions": fulfillment_options,
            "llmRecommendation": llm_analysis["recommendation"],
            "llmAnalyzed": llm_analysis["llm_analyzed"],
            "lastUpdated": datetime.now().isoformat()
        }

        duration = time.time() - start_time
        log_api_response(logger, "POST", "/check-inventory", 200, duration)
        metrics.record_request("POST", "/check-inventory", 200, duration)

        return jsonify({"status": "success", **result})

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/feedback', methods=['POST'])
def feedback_endpoint():
    """Collect feedback for inventory LLM"""
    try:
        data = request.json

        if llm_manager and hasattr(llm_manager, 'collect_feedback'):
            llm_manager.collect_feedback(
                prompt=f"inventory_check_{data.get('product_id')}",
                response=data.get('response'),
                rating=data.get('rating'),
                metadata=data.get('metadata', {})
            )

        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    logger.info("🚀 Starting Inventory Agent with Local LLM on port 5003")
    app.run(port=5003, debug=False)
