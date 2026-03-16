# -*- coding: utf-8 -*-
"""
Created on Sun Mar 15 03:25:00 2026

@author: HP
"""
import os
import psycopg2
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# -------------------------
# Connexion à PostgreSQL (Railway fournit DATABASE_URL)
# -------------------------
def get_conn():
    db_url = os.environ.get("DATABASE_URL")
    print("DATABASE_URL =", os.environ.get("DATABASE_URL"))
    if not db_url:
        raise Exception("DATABASE_URL n'est pas défini dans l'environnement")
    return psycopg2.connect(db_url)

# -------------------------
# Initialisation de la base de données
# -------------------------
def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id SERIAL PRIMARY KEY,
        customer_id TEXT,
        event_type TEXT,   -- type d'événement (order, cart, checkout, customer_update, search, click)
        product_id TEXT,
        query TEXT,
        event_data JSONB,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()

# -------------------------
# Fonction utilitaire pour sauvegarder les événements
# -------------------------
def save_event(customer_id, event_type, product_id, query, event_data):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO events (customer_id, event_type, product_id, query, event_data)
        VALUES (%s, %s, %s, %s, %s)
    """, (customer_id, event_type, product_id, query, json.dumps(event_data)))
    conn.commit()
    cursor.close()
    conn.close()

# -------------------------
# Endpoints pour les Webhooks Shopify
# -------------------------
@app.route("/orders/create", methods=["POST"])
def orders_create():
    data = request.json
    save_event(data.get("customer", {}).get("id"), "order", None, None, data)
    return "Commande reçue", 200

@app.route("/customers/update", methods=["POST"])
def customers_update():
    data = request.json
    print("DEBUG DATA:", data)  # Railway Logs
    try:
        customer_id = data.get("id") or data.get("customer", {}).get("id")
        print("DEBUG CUSTOMER_ID:", customer_id)
        save_event(customer_id, "customer_update", None, None, data)
        return "Client mis à jour", 200
    except Exception as e:
        print("ERROR in customers_update:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/checkouts/create", methods=["POST"])
def checkouts_create():
    data = request.json
    save_event(data.get("customer", {}).get("id"), "checkout", None, None, data)
    return "Paiement créé", 200

@app.route("/customers/update", methods=["POST"])
def customers_update():
    data = request.json
    print("DEBUG DATA:", data)  # يظهر فـ Railway Logs
    try:
        customer_id = data.get("id") or data.get("customer", {}).get("id")
        print("DEBUG CUSTOMER_ID:", customer_id)
        save_event(customer_id, "customer_update", None, None, data)
        return "Client mis à jour", 200
    except Exception as e:
        print("ERROR in customers_update:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# Endpoints personnalisés (search & click)
# -------------------------
@app.route("/events/search", methods=["POST"])
def track_search():
    data = request.json
    save_event(data.get("customer_id"), "search", None, data.get("query"), data)
    return "Recherche enregistrée", 200

@app.route("/events/click", methods=["POST"])
def track_click():
    data = request.json
    save_event(data.get("customer_id"), "click", data.get("product_id"), None, data)
    return "Clic enregistré", 200

# -------------------------
# Endpoint de recommandations simples
# -------------------------
@app.route("/recommendations/<customer_id>", methods=["GET"])
def recommendations(customer_id):
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
    return jsonify(rows)

# -------------------------
# Lancement du serveur Flask (compatible Railway)
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway fournit PORT automatiquement
    app.run(host="0.0.0.0", port=port)
