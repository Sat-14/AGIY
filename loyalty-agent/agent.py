from flask import Flask, request, jsonify

app = Flask(__name__)

# Mock user loyalty database
LOYALTY_DB = {
    "user_12345": {
        "userId": "user_12345",
        "loyaltyPoints": 1500,
        "pointValue": 0.5,  # 1 point = 0.5 INR
        "tier": "gold",
        "memberSince": "2023-01-15"
    },
    "user_67890": {
        "userId": "user_67890",
        "loyaltyPoints": 350,
        "pointValue": 0.5,
        "tier": "silver",
        "memberSince": "2024-03-22"
    }
}

# Mock coupon database
COUPONS_DB = {
    "SAVE10": {"type": "percentage", "value": 10, "description": "10% off on all items"},
    "SAVE50": {"type": "fixed", "value": 50, "description": "Flat ₹50 off"},
    "WELCOME20": {"type": "percentage", "value": 20, "description": "20% off for new users"},
    "FREESHIP": {"type": "free_shipping", "value": 0, "description": "Free shipping on all orders"},
    "FLAT100": {"type": "fixed", "value": 100, "description": "Flat ₹100 off on orders above ₹1000"}
}

# Customer segments and their offers
SEGMENT_OFFERS = {
    "new_customer": {
        "description": "Welcome! Get 20% off on your first purchase",
        "discount_type": "percentage",
        "discount_value": 20,
        "eligible_coupons": ["WELCOME20", "FREESHIP"]
    },
    "vip": {
        "description": "VIP Discount: 15% off on all items + free shipping",
        "discount_type": "percentage",
        "discount_value": 15,
        "eligible_coupons": ["SAVE10", "SAVE50", "FLAT100", "FREESHIP"]
    },
    "gold": {
        "description": "Gold Member: 10% off + extra loyalty points",
        "discount_type": "percentage",
        "discount_value": 10,
        "eligible_coupons": ["SAVE10", "SAVE50", "FREESHIP"]
    },
    "silver": {
        "description": "Silver Member: 5% off on all orders",
        "discount_type": "percentage",
        "discount_value": 5,
        "eligible_coupons": ["SAVE10", "FREESHIP"]
    },
    "regular": {
        "description": "Check our ongoing promotions for savings!",
        "discount_type": "none",
        "discount_value": 0,
        "eligible_coupons": ["SAVE10"]
    }
}

@app.route('/get-applicable-offers', methods=['POST'])
def get_applicable_offers():
    """
    Fetches all valid offers for a given user and their cart.
    Endpoint: POST /get-applicable-offers
    """
    data = request.get_json()

    user_id = data.get("userId") or data.get("user_id")
    cart_id = data.get("cartId") or data.get("cart_id")
    cart_amount = data.get("cartAmount") or data.get("cart_amount", 0)

    if not user_id or not cart_id:
        return jsonify({
            "status": "error",
            "message": "Missing required fields: userId and cartId are required."
        }), 400

    # Get user loyalty info
    user_loyalty = LOYALTY_DB.get(user_id, {
        "userId": user_id,
        "loyaltyPoints": 0,
        "pointValue": 0.5,
        "tier": "regular",
        "memberSince": "2025-01-01"
    })

    # Get segment-based offers
    segment = user_loyalty.get("tier", "regular")
    segment_offer = SEGMENT_OFFERS.get(segment, SEGMENT_OFFERS["regular"])

    # Get applicable coupons
    eligible_coupons = segment_offer.get("eligible_coupons", [])
    available_coupons = []

    for coupon_code in eligible_coupons:
        coupon = COUPONS_DB.get(coupon_code)
        if coupon:
            available_coupons.append({
                "offerId": coupon_code,
                "description": coupon["description"],
                "type": coupon["type"],
                "value": coupon["value"],
                "isApplicable": True
            })

    # Calculate loyalty points value
    loyalty_points_value = user_loyalty["loyaltyPoints"] * user_loyalty["pointValue"]
    is_redeemable = user_loyalty["loyaltyPoints"] >= 100  # Minimum 100 points to redeem

    return jsonify({
        "status": "success",
        "userId": user_id,
        "cartId": cart_id,
        "loyaltyPoints": {
            "balance": user_loyalty["loyaltyPoints"],
            "equivalentValue": round(loyalty_points_value, 2),
            "isRedeemable": is_redeemable,
            "tier": user_loyalty["tier"],
            "memberSince": user_loyalty["memberSince"]
        },
        "segmentOffer": {
            "description": segment_offer["description"],
            "discountType": segment_offer["discount_type"],
            "discountValue": segment_offer["discount_value"]
        },
        "availableCoupons": available_coupons,
        "recommendations": [
            f"You can save up to ₹{round(loyalty_points_value, 2)} by redeeming your loyalty points",
            f"As a {segment} member, you get {segment_offer['description']}"
        ]
    }), 200

@app.route('/apply-coupon', methods=['POST'])
def apply_coupon():
    """
    Applies a coupon code and calculates discount.
    Endpoint: POST /apply-coupon
    """
    data = request.get_json()

    user_id = data.get("userId") or data.get("user_id")
    cart_id = data.get("cartId") or data.get("cart_id")
    coupon_code = (data.get("couponCode") or data.get("coupon_code", "")).upper()
    cart_amount = data.get("cartAmount") or data.get("cart_amount", 0)

    if not user_id or not cart_id or not coupon_code:
        return jsonify({
            "status": "error",
            "message": "Missing required fields: userId, cartId, and couponCode are required."
        }), 400

    # Validate coupon
    coupon = COUPONS_DB.get(coupon_code)
    if not coupon:
        return jsonify({
            "status": "invalid",
            "message": f"Coupon code '{coupon_code}' is invalid or expired."
        }), 200

    # Calculate discount
    discount = 0
    shipping_discount = 0

    if coupon["type"] == "percentage":
        discount = (cart_amount * coupon["value"]) / 100
    elif coupon["type"] == "fixed":
        discount = coupon["value"]
    elif coupon["type"] == "free_shipping":
        shipping_discount = 50  # Mock shipping cost

    final_amount = max(cart_amount - discount, 0)

    return jsonify({
        "status": "success",
        "userId": user_id,
        "cartId": cart_id,
        "couponCode": coupon_code,
        "couponDescription": coupon["description"],
        "discount": round(discount, 2),
        "shippingDiscount": shipping_discount,
        "originalAmount": cart_amount,
        "finalAmount": round(final_amount, 2),
        "message": f"Coupon applied! You saved ₹{round(discount + shipping_discount, 2)}."
    }), 200

@app.route('/redeem-loyalty-points', methods=['POST'])
def redeem_loyalty_points():
    """
    Redeems loyalty points for a discount.
    Endpoint: POST /redeem-loyalty-points
    """
    data = request.get_json()

    user_id = data.get("userId") or data.get("user_id")
    cart_id = data.get("cartId") or data.get("cart_id")
    points_to_redeem = data.get("pointsToRedeem") or data.get("points_to_redeem", 0)
    cart_amount = data.get("cartAmount") or data.get("cart_amount", 0)

    if not user_id or not cart_id:
        return jsonify({
            "status": "error",
            "message": "Missing required fields: userId and cartId are required."
        }), 400

    # Get user loyalty info
    user_loyalty = LOYALTY_DB.get(user_id)
    if not user_loyalty:
        return jsonify({
            "status": "error",
            "message": "User loyalty account not found."
        }), 404

    # Validate points
    if points_to_redeem > user_loyalty["loyaltyPoints"]:
        return jsonify({
            "status": "insufficient",
            "message": f"Insufficient loyalty points. You have {user_loyalty['loyaltyPoints']} points available."
        }), 200

    if points_to_redeem < 100:
        return jsonify({
            "status": "error",
            "message": "Minimum 100 points required for redemption."
        }), 200

    # Calculate discount
    discount = points_to_redeem * user_loyalty["pointValue"]
    final_amount = max(cart_amount - discount, 0)

    # Update points (in real system, this would be persisted)
    remaining_points = user_loyalty["loyaltyPoints"] - points_to_redeem

    return jsonify({
        "status": "success",
        "userId": user_id,
        "cartId": cart_id,
        "pointsRedeemed": points_to_redeem,
        "discount": round(discount, 2),
        "originalAmount": cart_amount,
        "finalAmount": round(final_amount, 2),
        "remainingPoints": remaining_points,
        "message": f"Loyalty points redeemed! You saved ₹{round(discount, 2)}."
    }), 200

if __name__ == '__main__':
    print("\n--- Loyalty & Offers Agent (Flask API) Starting on Port 5006 ---")
    app.run(host='127.0.0.1', port=5006, debug=False)