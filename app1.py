# -*- coding: utf-8 -*-
"""
Created on Sun Mar 15 03:25:00 2026

@author: HP
"""
import os
import psycopg2
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from psycopg2.extras import Json

app = Flask(__name__)
CORS(app)

# إعداد logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response

def get_conn():
    db_url = os.environ.get("DATABASE_URL")
    logger.info(f"DATABASE_URL = {db_url}")
    if not db_url:
        raise Exception("DATABASE_URL n'est pas défini")
    return psycopg2.connect(db_url)

def init_db():
    logger.info("Initialisation DB...")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id SERIAL PRIMARY KEY,
        customer_id TEXT,
        event_type TEXT,
        product_id TEXT,
        query TEXT,
        event_data JSONB,
        page_url TEXT,
        referrer TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    cursor.close()
    conn.close()
    logger.info("DB initialisée")

try:
    init_db()
except Exception as e:
    logger.error(f"ERROR init_db: {str(e)}")

def save_event(customer_id, event_type, product_id, query, event_data, page_url=None, referrer=None):
    logger.info(f"save_event appelé avec customer_id={customer_id}, event_type={event_type}")
    logger.debug(f"event_data = {event_data}")
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (customer_id, event_type, product_id, query, event_data, page_url, referrer, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, DEFAULT)
        """, (
            customer_id if customer_id else "unknown",
            event_type if event_type else "unknown",
            product_id,
            query,
            Json(event_data if event_data else {}),
            page_url,
            referrer
        ))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Event sauvegardé")
    except Exception as e:
        logger.error(f"ERROR in save_event: {str(e)}")

@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200

@app.route("/events/search", methods=["POST"])
def track_search():
    data = request.json
    logger.info(f"/events/search data = {data}")
    if not data:
        return jsonify({"status": "error", "message": "request.json est vide"}), 400
    save_event(
        data.get("customer_id"),
        "search",
        None,
        data.get("query"),
        data,
        page_url=data.get("page_url"),
        referrer=data.get("referrer")
    )
    return "Recherche enregistrée", 200

@app.route("/events/click", methods=["POST"])
def track_click():
    data = request.json
    logger.info(f"/events/click data = {data}")
    if not data:
        return jsonify({"status": "error", "message": "request.json est vide"}), 400
    save_event(
        data.get("customer_id"),
        "click",
        data.get("product_id"),
        None,
        data,
        page_url=data.get("page_url"),
        referrer=data.get("referrer")
    )
    return "Clic enregistré", 200

@app.route("/recommendations/<customer_id>", methods=["GET"])
def recommendations(customer_id):
    logger.info(f"/recommendations appelé pour customer_id = {customer_id}")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT product_id, COUNT(*) as clicks
        FROM events
        WHERE customer_id = %s AND event_type = 'click'
        GROUP BY product_id
        ORDER BY clicks DESC
        LIMIT 5
    """, (customer_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    logger.info(f"Résultat recommandations = {rows}")
    return jsonify(rows)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Démarrage du serveur Flask sur le port {port}")
    app.run(host="0.0.0.0", port=port)
