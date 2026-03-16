# -*- coding: utf-8 -*-
"""
Created on Sun Mar 15 03:25:00 2026

@author: HP
"""

import os
import psycopg2
import psycopg2.pool
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# -------------------------
# Connexion PostgreSQL avec Connection Pool
# -------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

# Création d'un pool de connexions pour améliorer les performances
pool = psycopg2.pool.SimpleConnectionPool(
    1, 10, dsn=DATABASE_URL
)

def get_conn():
    """Obtenir une connexion depuis le pool"""
    try:
        return pool.getconn()
    except Exception as e:
        print("Erreur connexion DB:", e)
        raise

def release_conn(conn):
    """Libérer la connexion et la remettre dans le pool"""
    if conn:
        pool.putconn(conn)

def init_db():
    """Initialiser la base de données et créer la table events si elle n'existe pas"""
    conn = get_conn()
    try:
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
    except Exception as e:
        print("Erreur init_db:", e)
    finally:
        release_conn(conn)

init_db()

# -------------------------
# Fonction utilitaire pour sauvegarder les événements
# -------------------------
def save_event(customer_id, event_type, product_id, query, event_data):
    """Sauvegarder un événement dans la table events"""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (customer_id, event_type, product_id, query, event_data)
            VALUES (%s, %s, %s, %s, %s)
        """, (customer_id, event_type, product_id, query, json.dumps(event_data)))
        conn.commit()
        cursor.close()
    except Exception as e:
        print("Erreur save_event:", e)
    finally:
        release_conn(conn)

# -------------------------
# Endpoints pour les Webhooks Shopify
# -------------------------
@app.route("/orders/create", methods=["POST"])
def orders_create():
    """Webhook pour la création de commande"""
    try:
        data = request.json
        save_event(data.get("customer", {}).get("id"), "order", None, None, data)
        return "Commande reçue", 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/carts/update", methods=["POST"])
def carts_update():
    """Webhook pour la mise à jour du panier"""
    try:
        data = request.json
        product_id = None
        if "line_items" in data and len(data["line_items"]) > 0:
            product_id = data["line_items"][0].get("product_id")
        save_event(data.get("customer_id"), "cart", product_id, None, data)
        return "Panier mis à jour", 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/checkouts/create", methods=["POST"])
def checkouts_create():
    """Webhook pour la création de checkout"""
    try:
        data = request.json
        save_event(data.get("customer_id"), "checkout", None, None, data)
        return "Paiement créé", 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/customers/update", methods=["POST"])
def customers_update():
    """Webhook pour la mise à jour du client"""
    try:
        data = request.json
        save_event(data.get("id"), "customer_update", None, None, data)
        return "Client mis à jour", 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------
# Endpoints personnalisés (search & click)
# -------------------------
@app.route("/events/search", methods=["POST"])
def track_search():
    """Endpoint pour enregistrer une recherche"""
    try:
        data = request.json
        save_event(data.get("customer_id"), "search", None, data.get("query"), data)
        return "Recherche enregistrée", 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/events/click", methods=["POST"])
def track_click():
    """Endpoint pour enregistrer un clic produit"""
    try:
        data = request.json
        save_event(data.get("customer_id"), "click", data.get("product_id"), None, data)
        return "Clic enregistré", 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------
# Endpoint de recommandations simples
# -------------------------
@app.route("/recommendations/<customer_id>", methods=["GET"])
def recommendations(customer_id):
    """Retourner les 5 produits les plus cliqués par un client"""
    conn = get_conn()
    try:
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
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        release_conn(conn)

# -------------------------
# Lancement du serveur Flask (compatible Railway)
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway fournit PORT automatiquement
    app.run(host="0.0.0.0", port=port)