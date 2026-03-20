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
CORS(app, resources={r"/events/*": {"origins": "https://modestyle-8979.myshopify.com"}})  

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
logger.info(f"DATABASE_URL utilisé: {DATABASE_URL}")

def save_event(customer_id, event_type, query=None, product_id=None, timestamp=None, page_url=None, referrer=None):
    logger.info(f"save_event appelé avec customer_id={customer_id}, event_type={event_type}")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Vérifier si la table existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'events'
            );
        """)
        exists = cursor.fetchone()[0]
        if not exists:
            logger.error("Le tableau 'events' n'existe pas dans cette base.")
            return

        # Log des valeurs avant INSERT
        logger.info("Tentative INSERT avec valeurs: %s", (
            customer_id if customer_id else "unknown",
            event_type if event_type else "unknown",
            product_id,
            query,
            timestamp or datetime.utcnow(),
            page_url,
            referrer
        ))

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

        # ✅ afficher le nombre d'événements après insertion
        cursor.execute("SELECT COUNT(*) FROM events;")
        count = cursor.fetchone()[0]
        logger.info(f"Nombre total d'événements dans la base: {count}")

        # ✅ afficher le dernier événement inséré
        cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT 1;")
        last_event = cursor.fetchone()
        logger.info(f"Dernier événement inséré: {last_event}")

        cursor.close()
        conn.close()
        logger.info("Event sauvegardé dans la base")
    except Exception as e:
        logger.error(f"Erreur dans save_event: {str(e)}")

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
    logger.info(f"/events/click data = {data}")
    if not data:
        return jsonify({"status": "error", "message": "request.json est vide"}), 400
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
