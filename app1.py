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

def save_event(customer_id, event_type, query=None, product_id=None):
    logger.info(f"save_event appelé avec customer_id={customer_id}, event_type={event_type}")
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
            logger.error("Le tableau 'events' n'existe pas dans cette base.")
            return
        cursor.execute("""
            INSERT INTO events (customer_id, event_type, product_id, query, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            customer_id if customer_id else "unknown",
            event_type if event_type else "unknown",
            product_id,
            query,
            datetime.utcnow()
        ))
        conn.commit()
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
        product_id=None
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
        query=None,
        product_id=data.get("product_id")
    )
    return "Clic enregistré", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Démarrage du serveur Flask sur le port {port}")
    app.run(host="0.0.0.0", port=port)
