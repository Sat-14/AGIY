import json
import sys
import os
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
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
tracing = TracingManager("inventory-agent", "1.0.0")
metrics = MetricsManager("inventory-agent")
logging_config = StructuredLogger("inventory-agent")
logger = logging_config.get_logger()

# Initialize MongoDB
db_manager = get_db_manager()
inventory_collection = db_manager.get_collection("inventory")

# Create Flask app
app = Flask(__name__)

# Instrument Flask app
tracing.instrument_flask_app(app)
metrics.create_metrics_endpoint(app)


@trace_function
def get_product_from_db(product_id):
    """Fetch product inventory from MongoDB"""
    try:
        start_time = time.time()

        product = inventory_collection.find_one({"product_id": product_id})

        duration = time.time() - start_time
        log_db_operation(logger, "inventory", "find_one", product_id, duration)
        metrics.record_db_operation("inventory", "find", "success", duration)

        return product

    except Exception as e:
        log_error(logger, e, {"operation": "get_product_from_db", "product_id": product_id})
        metrics.record_error("product_fetch_error")
        return None


@trace_function
def get_warehouse_inventory(product_id, attributes):
    """Check warehouse inventory from DB or fallback to mock"""
    product = get_product_from_db(product_id)

    if product and "warehouses" in product:
        return product["warehouses"]

    # Fallback to mock data
    logger.warning(f"Using mock warehouse data for {product_id}")

    warehouses = {
        "WH_NORTH": {"name": "North Regional Warehouse", "location": "Delhi NCR"},
        "WH_SOUTH": {"name": "South Regional Warehouse", "location": "Bangalore"},
        "WH_WEST": {"name": "West Regional Warehouse", "location": "Mumbai"},
        "WH_EAST": {"name": "East Regional Warehouse", "location": "Kolkata"}
    }

    if "OUT_OF_STOCK" in product_id:
        warehouse_stock = {"WH_NORTH": 0, "WH_SOUTH": 0, "WH_WEST": 0, "WH_EAST": 0}
    elif "LOW_STOCK" in product_id:
        warehouse_stock = {"WH_NORTH": 3, "WH_SOUTH": 2, "WH_WEST": 1, "WH_EAST": 0}
    else:
        warehouse_stock = {"WH_NORTH": 150, "WH_SOUTH": 80, "WH_WEST": 120, "WH_EAST": 60}

    return [
        {
            "warehouseId": wh_id,
            "warehouseName": wh_data["name"],
            "location": wh_data["location"],
            "stockLevel": warehouse_stock[wh_id],
            "estimatedShippingTime": "2-3 days"
        }
        for wh_id, wh_data in warehouses.items()
    ]


@trace_function
def get_store_inventory(product_id, location_context, attributes):
    """Check store inventory from DB or fallback to mock"""
    product = get_product_from_db(product_id)

    if product and "stores" in product:
        stores = product["stores"]
    else:
        # Fallback to mock data
        logger.warning(f"Using mock store data for {product_id}")

        if "OUT_OF_STOCK" in product_id:
            all_stores = [
                {
                    "storeId": "STORE_SCW_DL",
                    "storeName": "Select Citywalk",
                    "address": "District Centre, Saket, New Delhi - 110017",
                    "city": "Delhi",
                    "region": "North",
                    "stockLevel": 0,
                    "stockDescriptor": "out_of_stock"
                }
            ]
        elif "LOW_STOCK" in product_id:
            all_stores = [
                {
                    "storeId": "STORE_SCW_DL",
                    "storeName": "Select Citywalk",
                    "address": "District Centre, Saket, New Delhi - 110017",
                    "city": "Delhi",
                    "region": "North",
                    "stockLevel": 1,
                    "stockDescriptor": "low"
                }
            ]
        else:
            all_stores = [
                {
                    "storeId": "STORE_SCW_DL",
                    "storeName": "Select Citywalk",
                    "address": "District Centre, Saket, New Delhi - 110017",
                    "city": "Delhi",
                    "region": "North",
                    "stockLevel": 5,
                    "stockDescriptor": "low"
                },
                {
                    "storeId": "STORE_DLF_DL",
                    "storeName": "DLF Promenade",
                    "address": "3, Nelson Mandela Road, Vasant Kunj, New Delhi - 110070",
                    "city": "Delhi",
                    "region": "North",
                    "stockLevel": 2,
                    "stockDescriptor": "low"
                },
                {
                    "storeId": "STORE_PHX_MUM",
                    "storeName": "Phoenix Palladium",
                    "address": "High Street Phoenix, Lower Parel, Mumbai - 400013",
                    "city": "Mumbai",
                    "region": "West",
                    "stockLevel": 12,
                    "stockDescriptor": "high"
                }
            ]
        stores = all_stores

    # Filter by location context
    if location_context and location_context.get("city"):
        city = location_context["city"].lower()
        filtered_stores = [
            store for store in stores
            if city in store.get("city", "").lower() or city in store.get("region", "").lower()
        ]
    else:
        filtered_stores = stores

    return filtered_stores


@trace_function
def calculate_online_status(warehouses):
    """Determine online availability based on warehouse stock"""
    total_stock = sum(wh["stockLevel"] for wh in warehouses)

    if total_stock == 0:
        return "out_of_stock"
    elif total_stock < 50:
        return "low_stock"
    else:
        return "in_stock"


@trace_function
def check_inventory(product_id, attributes, location_context):
    """Core inventory checking logic with MongoDB integration"""
    logger.info(f"Checking inventory for product: {product_id}")

    with tracing.create_span("check_inventory") as span:
        span.set_attribute("product_id", product_id)
        span.set_attribute("location", location_context.get("city", "N/A") if location_context else "N/A")

        # Get warehouse inventory
        warehouses = get_warehouse_inventory(product_id, attributes)
        online_status = calculate_online_status(warehouses)
        total_online_stock = sum(wh["stockLevel"] for wh in warehouses)

        # Get store inventory
        stores = get_store_inventory(product_id, location_context, attributes)

        # Determine fulfillment options
        fulfillment_options = []
        stores_with_stock = [s for s in stores if s["stockLevel"] > 0]

        if online_status == "in_stock" or online_status == "low_stock":
            fulfillment_options.append({
                "type": "ship_to_home",
                "available": True,
                "estimatedDelivery": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
                "shippingCost": 0 if total_online_stock > 100 else 99,
                "urgency": "High - Limited stock!" if online_status == "low_stock" else None
            })
        else:
            fulfillment_options.append({
                "type": "ship_to_home",
                "available": False,
                "message": "Currently out of stock online. Check store availability or request notification."
            })

        if len(stores_with_stock) > 0:
            fulfillment_options.append({
                "type": "click_and_collect",
                "available": True,
                "availableStores": len(stores_with_stock),
                "message": "Reserve online and pick up from store"
            })
            fulfillment_options.append({
                "type": "in_store_purchase",
                "available": True,
                "availableStores": len(stores_with_stock),
                "message": "Try and buy at our stores"
            })
        else:
            fulfillment_options.append({
                "type": "in_store_purchase",
                "available": False,
                "message": "Currently unavailable in nearby stores."
            })

        # Record metrics
        product_category = attributes.get("category", "unknown")
        metrics.inventory_checks.labels(
            product_category=product_category,
            stock_status=online_status
        ).inc()

        logger.info(f"Inventory check complete: {online_status}, {len(stores)} stores")

        return {
            "productId": product_id,
            "onlineStatus": online_status,
            "onlineStockLevel": total_online_stock,
            "warehouses": warehouses,
            "availableStores": stores,
            "fulfillmentOptions": fulfillment_options,
            "lastUpdated": datetime.now().isoformat()
        }


@app.route('/check-inventory', methods=['POST'])
def check_inventory_endpoint():
    """API endpoint for inventory checking"""
    start_time = time.time()

    try:
        data = request.json
        log_api_request(logger, "POST", "/check-inventory", data)

        product_id = data.get('product_id')
        attributes = data.get('attributes', {})
        location_context = data.get('location_context', {})

        if not product_id:
            response = {"status": "error", "message": "Missing product_id"}
            return jsonify(response), 400

        result = check_inventory(product_id, attributes, location_context)

        duration = time.time() - start_time
        log_api_response(logger, "POST", "/check-inventory", 200, duration)
        metrics.record_request("POST", "/check-inventory", 200, duration)

        return jsonify({"status": "success", **result})

    except Exception as e:
        duration = time.time() - start_time
        log_error(logger, e, {"endpoint": "/check-inventory"})
        log_api_response(logger, "POST", "/check-inventory", 500, duration)
        metrics.record_request("POST", "/check-inventory", 500, duration)
        metrics.record_error(type(e).__name__)

        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    logger.info("Starting Inventory Agent on port 5003")
    app.run(port=5003, debug=False)
