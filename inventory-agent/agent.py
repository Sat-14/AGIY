import json
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

def get_warehouse_inventory(product_id, attributes):
    """
    Simulates checking warehouse inventory.
    In production, this would query a real-time inventory management system.
    """
    warehouses = {
        "WH_NORTH": {"name": "North Regional Warehouse", "location": "Delhi NCR"},
        "WH_SOUTH": {"name": "South Regional Warehouse", "location": "Bangalore"},
        "WH_WEST": {"name": "West Regional Warehouse", "location": "Mumbai"},
        "WH_EAST": {"name": "East Regional Warehouse", "location": "Kolkata"}
    }

    # Mock warehouse stock levels - including edge cases
    # Use product_id to simulate different scenarios
    if "OUT_OF_STOCK" in product_id:
        warehouse_stock = {
            "WH_NORTH": 0,
            "WH_SOUTH": 0,
            "WH_WEST": 0,
            "WH_EAST": 0
        }
    elif "LOW_STOCK" in product_id:
        warehouse_stock = {
            "WH_NORTH": 3,
            "WH_SOUTH": 2,
            "WH_WEST": 1,
            "WH_EAST": 0
        }
    else:
        warehouse_stock = {
            "WH_NORTH": 150,
            "WH_SOUTH": 80,
            "WH_WEST": 120,
            "WH_EAST": 60
        }

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

def get_store_inventory(product_id, location_context, attributes):
    """
    Checks inventory across physical stores.
    Supports filtering by city/region.
    Includes edge cases for out-of-stock and low-stock scenarios.
    """
    # Mock store database - modify based on product_id for edge cases
    if "OUT_OF_STOCK" in product_id:
        # All stores are out of stock
        all_stores = [
            {
                "storeId": "STORE_SCW_DL",
                "storeName": "Select Citywalk",
                "address": "District Centre, Saket, New Delhi - 110017",
                "city": "Delhi",
                "region": "North",
                "stockLevel": 0,
                "stockDescriptor": "out_of_stock"
            },
            {
                "storeId": "STORE_DLF_DL",
                "storeName": "DLF Promenade",
                "address": "3, Nelson Mandela Road, Vasant Kunj, New Delhi - 110070",
                "city": "Delhi",
                "region": "North",
                "stockLevel": 0,
                "stockDescriptor": "out_of_stock"
            },
            {
                "storeId": "STORE_AMB_DL",
                "storeName": "Ambience Mall",
                "address": "Ambience Island, NH-8, Gurgaon - 122002",
                "city": "Gurgaon",
                "region": "North",
                "stockLevel": 0,
                "stockDescriptor": "out_of_stock"
            }
        ]
    elif "LOW_STOCK" in product_id:
        # Very limited stock across stores
        all_stores = [
            {
                "storeId": "STORE_SCW_DL",
                "storeName": "Select Citywalk",
                "address": "District Centre, Saket, New Delhi - 110017",
                "city": "Delhi",
                "region": "North",
                "stockLevel": 1,
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
                "stockLevel": 1,
                "stockDescriptor": "low"
            }
        ]
    else:
        # Normal stock levels
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
                "storeId": "STORE_AMB_DL",
                "storeName": "Ambience Mall",
                "address": "Ambience Island, NH-8, Gurgaon - 122002",
                "city": "Gurgaon",
                "region": "North",
                "stockLevel": 8,
                "stockDescriptor": "medium"
            },
            {
                "storeId": "STORE_PHX_MUM",
                "storeName": "Phoenix Palladium",
                "address": "High Street Phoenix, Lower Parel, Mumbai - 400013",
                "city": "Mumbai",
                "region": "West",
                "stockLevel": 12,
                "stockDescriptor": "high"
            },
            {
                "storeId": "STORE_UB_BLR",
                "storeName": "UB City Mall",
                "address": "24, Vittal Mallya Road, Bangalore - 560001",
                "city": "Bangalore",
            "region": "South",
            "stockLevel": 6,
            "stockDescriptor": "medium"
        }
    ]

    # Filter by location context if provided
    if location_context and location_context.get("city"):
        city = location_context["city"].lower()
        filtered_stores = [
            store for store in all_stores
            if city in store["city"].lower() or city in store["region"].lower()
        ]
    else:
        filtered_stores = all_stores

    return filtered_stores

def calculate_online_status(warehouses):
    """Determine online availability based on warehouse stock"""
    total_stock = sum(wh["stockLevel"] for wh in warehouses)

    if total_stock == 0:
        return "out_of_stock"
    elif total_stock < 50:
        return "low_stock"
    else:
        return "in_stock"

def check_inventory(product_id, attributes, location_context):
    """
    Core inventory checking logic.
    Provides real-time stock across:
    - Online (warehouses)
    - Physical stores
    - Fulfillment options
    """
    print("--- INVENTORY AGENT ACTION ---")
    print(f"Checking inventory for product: {product_id}")
    print(f"Attributes: {attributes}")
    print(f"Location context: {location_context}")

    # Get warehouse inventory
    warehouses = get_warehouse_inventory(product_id, attributes)
    online_status = calculate_online_status(warehouses)
    total_online_stock = sum(wh["stockLevel"] for wh in warehouses)

    # Get store inventory
    stores = get_store_inventory(product_id, location_context, attributes)

    # Determine fulfillment options with edge case handling
    fulfillment_options = []

    # Filter stores with stock > 0
    stores_with_stock = [s for s in stores if s["stockLevel"] > 0]

    if online_status == "in_stock" or online_status == "low_stock":
        fulfillment_options.append({
            "type": "ship_to_home",
            "available": True,
            "estimatedDelivery": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
            "shippingCost": 0 if total_online_stock > 100 else 99,
            "urgency": "High - Limited stock!" if online_status == "low_stock" else None
        })
    elif online_status == "out_of_stock":
        fulfillment_options.append({
            "type": "ship_to_home",
            "available": False,
            "message": "Currently out of stock online. Check store availability or request notification when back in stock."
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
            "message": "Currently unavailable in nearby stores. Consider alternative products or check back later."
        })

    print(f"Online status: {online_status}, Store availability: {len(stores)} stores")

    return {
        "productId": product_id,
        "onlineStatus": online_status,
        "onlineStockLevel": total_online_stock,
        "warehouses": warehouses,
        "availableStores": stores,
        "fulfillmentOptions": fulfillment_options,
        "lastUpdated": datetime.now().isoformat()
    }

# Create Flask app
app = Flask(__name__)

@app.route('/check-inventory', methods=['POST'])
def check_inventory_endpoint():
    """API endpoint for inventory checking"""
    data = request.json

    product_id = data.get('product_id')
    attributes = data.get('attributes', {})
    location_context = data.get('location_context', {})

    if not product_id:
        return jsonify({"status": "error", "message": "Missing product_id"}), 400

    try:
        result = check_inventory(product_id, attributes, location_context)
        return jsonify({"status": "success", **result})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5003, debug=False)
