from flask import Flask, jsonify, request
from flask_cors import CORS

from analytics import summarize

app = Flask(__name__)
CORS(app)

PRODUCTS = [
    {
        "id": 1,
        "brand": "Vincent Chase",
        "name": "VC E13405 Black Full Rim Round",
        "image": "https://placehold.co/300x200?text=VC+Frame",
        "rating": 4.8,
        "price": 1500,
        "original_price": 2000,
        "discount_pct": 25,
        "promo_code": "SINGLE",
        "colors": 4,
    },
    {
        "id": 2,
        "brand": "Lenskart Air",
        "name": "Air LA E14231 Blue Full Rim Rectangle",
        "image": "https://placehold.co/300x200?text=Air+Frame",
        "rating": 4.85,
        "price": 1800,
        "original_price": 2400,
        "discount_pct": 25,
        "promo_code": "SINGLE",
        "colors": 3,
    },
    {
        "id": 3,
        "brand": "John Jacobs",
        "name": "JJ E12987 Tortoise Full Rim Square",
        "image": "https://placehold.co/300x200?text=JJ+Frame",
        "rating": 4.7,
        "price": 2200,
        "original_price": 3000,
        "discount_pct": 27,
        "promo_code": "SINGLE",
        "colors": 5,
    },
    {
        "id": 4,
        "brand": "Vincent Chase",
        "name": "VC E10122 Gunmetal Half Rim Aviator",
        "image": "https://placehold.co/300x200?text=VC+Aviator",
        "rating": 4.6,
        "price": 1650,
        "original_price": 2200,
        "discount_pct": 25,
        "promo_code": "SINGLE",
        "colors": 2,
    },
]


@app.route("/api/products", methods=["GET"])
def get_products():
    brand = request.args.get("brand")
    sort_by = request.args.get("sort")

    result = PRODUCTS
    if brand:
        result = [p for p in result if p["brand"].lower() == brand.lower()]
    if sort_by == "price_low_high":
        result = sorted(result, key=lambda p: p["price"])
    elif sort_by == "price_high_low":
        result = sorted(result, key=lambda p: p["price"], reverse=True)
    elif sort_by == "rating":
        result = sorted(result, key=lambda p: p["rating"], reverse=True)

    return jsonify({"count": len(result), "products": result})


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if product is None:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product)


@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    return jsonify(summarize(PRODUCTS))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
