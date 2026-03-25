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
from flask_cors import CORS 

app = Flask(__name__)
CORS(app, resources={r"/events/*": {"origins": "*"}})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app1")

DATABASE_URL = os.environ.get("DATABASE_URL")
logger.info(f"DATABASE_URL utilisé: {DATABASE_URL}")

def save_event(customer_id, event_type, query=None, product_id=None, timestamp=None, page_url=None, referrer=None):
    print(">>> save_event CALLED <<<")   # للتأكد أن الدالة تنادات
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'events'
            );
        """)
        exists = cursor.fetchone()[0]
        if not exists:
            print(">>> TABLE 'events' NOT FOUND <<<")
            return

        print(">>> Tentative INSERT <<<")
        cursor.execute("""
            INSERT INTO events (customer_id, event_type, product_id, query, timestamp, page_url, referrer)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            customer_id if customer_id else "unknown",
            event_type if event_type else "unknown",
            product_id,
            query,
            timestamp or datetime.utcnow(),
            page_url,
            referrer
        ))

        conn.commit()
        print(">>> INSERT DONE <<<")

        cursor.close()
        conn.close()
        print(">>> Event sauvegardé <<<")
    except Exception as e:
        print(f">>> ERROR in save_event: {str(e)}")

@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200

@app.route("/events/search", methods=["POST"])
def track_search():
    data = request.json
    print(">>> /events/search CALLED <<<")
    print(f">>> DATA: {data}")
    if not data:
        print(">>> request.json est vide <<<")
        return jsonify({"status": "error", "message": "request.json est vide"}), 400
    print(">>> Calling save_event <<<")
    save_event(
        data.get("customer_id"),
        "search",
        query=data.get("query"),
        product_id=None,
        timestamp=data.get("timestamp"),
        page_url=data.get("page_url"),
        referrer=data.get("referrer")
    )
    return jsonify({"status": "success", "event_type": "search"}), 200

@app.route("/events/click", methods=["POST"])
def track_click():
    data = request.json
    print(">>> /events/click CALLED <<<")
    print(f">>> DATA: {data}")
    if not data:
        print(">>> request.json est vide <<<")
        return jsonify({"status": "error", "message": "request.json est vide"}), 400
    print(">>> Calling save_event <<<")
    save_event(
        data.get("customer_id"),
        "click",
        query=None,
        product_id=data.get("product_id"),
        timestamp=data.get("timestamp"),
        page_url=data.get("page_url"),
        referrer=data.get("referrer")
    )
    return jsonify({"status": "success", "event_type": "click"}), 200

@app.before_request
def log_request_info():
    logger.info(f"Requête reçue: {request.method} {request.url}")
    logger.info(f"Headers: {request.headers}")
    logger.info(f"Body brut: {request.get_data()}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Démarrage du serveur Flask sur le port {port}")
    app.run(host="0.0.0.0", port=port)
