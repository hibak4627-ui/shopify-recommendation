# -*- coding: utf-8 -*-
"""
Created on Sun Mar 15 03:25:00 2026

@author: HP
"""
import os
import psycopg2
import json
from flask import Flask, request, jsonify
from flask_cors import CORS   # Import du module CORS

app = Flask(__name__)
CORS(app)  # Autoriser toutes les origines (utile pour Shopify)

print("DEBUG: Flask app starting...")

# -------------------------
# Ajouter les headers CORS après chaque réponse
# -------------------------
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response

# -------------------------
# Connexion à PostgreSQL (Railway fournit DATABASE_URL)
# -------------------------
def get_conn():
    db_url = os.environ.get("DATABASE_URL")
    print("DEBUG: DATABASE_URL =", db_url)
    if not db_url:
        raise Exception("DATABASE_URL n'est pas défini dans l'environnement")
    return psycopg2.connect(db_url)

# -------------------------
# Initialisation de la base de données
# -------------------------
def init_db():
    print("DEBUG: Initialisation DB...")
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
    print("DEBUG: DB initialisée")

init_db()

# -------------------------
# Fonction utilitaire pour sauvegarder les événements
# -------------------------
def save_event(customer_id, event_type, product_id, query, event_data, page_url=None, referrer=None, timestamp=None):
    print(f"DEBUG: save_event appelé avec customer_id={customer_id}, event_type={event_type}")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO events (customer_id, event_type, product_id, query, event_data, page_url, referrer, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (customer_id, event_type, product_id, query, json.dumps(event_data), page_url, referrer, timestamp))
    conn.commit()
    cursor.close()
    conn.close()
    print("DEBUG: Event sauvegardé")

# -------------------------
# Webhooks Shopify
# -------------------------
@app.route("/orders/create", methods=["POST"])
def orders_create():
    data = request.json
    print("DEBUG: /orders/create data =", data)
    save_event(data.get("customer", {}).get("id"), "order", None, None, data)
    return "Commande reçue", 200

@app.route("/carts/update", methods=["POST"])
def carts_update():
    data = request.json
    print("DEBUG: /carts/update data =", data)
    product_id = None
    if "line_items" in data and len(data["line_items"]) > 0:
        product_id = data["line_items"][0].get("product_id")
    save_event(data.get("customer_id"), "cart", product_id, None, data)
    return "Panier mis à jour", 200

@app.route("/checkouts/create", methods=["POST"])
def checkouts_create():
    data = request.json
    print("DEBUG: /checkouts/create data =", data)
    save_event(data.get("customer", {}).get("id"), "checkout", None, None, data)
    return "Paiement créé", 200

@app.route("/customers/update", methods=["POST"])
def customers_update():
    data = request.json
    print("DEBUG: /customers/update data =", data)
    try:
        customer_id = data.get("id") or data.get("customer", {}).get("id")
        print("DEBUG CUSTOMER_ID:", customer_id)
        save_event(customer_id, "customer_update", None, None, data)
        return "Client mis à jour", 200
    except Exception as e:
        print("ERROR in customers_update:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# Actions personnalisées (search & click)
# -------------------------
@app.route("/events/search", methods=["POST"])
def track_search():
    data = request.json
    print("DEBUG: /events/search data =", data)
    save_event(
        data.get("customer_id"),
        "search",
        None,
        data.get("query"),
        data,
        page_url=data.get("page_url"),
        referrer=data.get("referrer"),
        timestamp=data.get("timestamp")
    )
    return "Recherche enregistrée", 200

@app.route("/events/click", methods=["POST"])
def track_click():
    data = request.json
    print("DEBUG: /events/click data =", data)
    save_event(
        data.get("customer_id"),
        "click",
        data.get("product_id"),
        None,
        data,
        page_url=data.get("page_url"),
        referrer=data.get("referrer"),
        timestamp=data.get("timestamp")
    )
    return "Clic enregistré", 200

# -------------------------
# Recommandations
# -------------------------
@app.route("/recommendations/<customer_id>", methods=["GET"])
def recommendations(customer_id):
    print("DEBUG: /recommendations appelé pour customer_id =", customer_id)
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
    print("DEBUG: Résultat recommandations =", rows)
    return jsonify(rows)

# -------------------------
# Lancement du serveur
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"DEBUG: Démarrage du serveur Flask sur le port {port}")
    app.run(host="0.0.0.0", port=port)
