# -*- coding: utf-8 -*-
"""
Created on Sun Mar 15 03:25:00 2026

@author: HP
"""
import os
import psycopg2
import logging
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

def save_event(customer_id, event_type, query=None, product_id=None, page_url=None, referrer=None):
    logger.info(f"save_event appelé avec customer_id={customer_id}, event_type={event_type}")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (customer_id, event_type, product_id, query, timestamp, page_url, referrer)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            customer_id if customer_id else "unknown",
            event_type if event_type else "unknown",
            product_id,
            query,
            datetime.utcnow(),
            page_url,
            referrer
        ))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(">>> INSERT DONE <<<")
        return True
    except Exception as e:
        logger.error(f"Erreur dans save_event: {str(e)}")
        return False

# --- Route de test ---
@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200

# --- Routes front-end (search / click) ---
@app.route("/events/search", methods=["POST"])
def track_search():
    data = request.json
    logger.info(f"/events/search data = {data}")
    if not data:
        return jsonify({"status": "error", "message": "request.json est vide"}), 400
    ok = save_event(
        data.get("customer_id"),
        "search",
        query=data.get("query"),
        product_id=None,
        page_url=data.get("page_url"),
        referrer=data.get("referrer")
    )
    return jsonify({"status": "success" if ok else "error"}), 200 if ok else 500

@app.route("/events/click", methods=["POST"])
def track_click():
    data = request.json
    logger.info(f"/events/click data = {data}")
    if not data:
        return jsonify({"status": "error", "message": "request.json est vide"}), 400
    ok = save_event(
        data.get("customer_id"),
        "click",
        query=None,
        product_id=data.get("product_id"),
        page_url=data.get("page_url"),
        referrer=data.get("referrer")
    )
    return jsonify({"status": "success" if ok else "error"}), 200 if ok else 500

# --- Routes webhooks Shopify ---
@app.route("/orders/create", methods=["POST"])
def order_created():
    data = request.json
    logger.info(f"Webhook order_created data = {data}")
    ok = save_event(
        data.get("customer", {}).get("id"),
        "order_created"
    )
    return jsonify({"status": "success" if ok else "error"}), 200 if ok else 500

@app.route("/carts/update", methods=["POST"])
def cart_updated():
    data = request.json
    logger.info(f"Webhook cart_updated data = {data}")
    ok = save_event(
        data.get("customer_id"),
        "cart_updated"
    )
    return jsonify({"status": "success" if ok else "error"}), 200 if ok else 500

@app.route("/checkouts/create", methods=["POST"])
def checkout_created():
    data = request.json
    logger.info(f"Webhook checkout_created data = {data}")
    ok = save_event(
        data.get("customer_id"),
        "checkout_created"
    )
    return jsonify({"status": "success" if ok else "error"}), 200 if ok else 500

@app.route("/customers/update", methods=["POST"])
def customer_updated():
    data = request.json
    logger.info(f"Webhook customer_updated data = {data}")
    ok = save_event(
        data.get("id"),
        "customer_updated"
    )
    return jsonify({"status": "success" if ok else "error"}), 200 if ok else 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Démarrage du serveur Flask sur le port {port}")
    app.run(host="0.0.0.0", port=port)
