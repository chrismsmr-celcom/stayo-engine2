"""
Database Engine — SQLite pour le MVP
"""

import sqlite3
import json
import os
from typing import Dict, List, Any

# Chemin vers la base de données
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stayo.db")


def get_db():
    """Retourne une connexion à la base de données"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Initialise les tables si elles n'existent pas"""
    conn = get_db()
    
    # Table des voyageurs
    conn.execute("""CREATE TABLE IF NOT EXISTS travelers (
        id TEXT PRIMARY KEY,
        name TEXT,
        email TEXT,
        preferences TEXT DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Table des voyages
    conn.execute("""CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        traveler_id TEXT,
        query TEXT,
        intent TEXT,
        context TEXT,
        recommendations TEXT,
        clicked_hotel_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Table des clics
    conn.execute("""CREATE TABLE IF NOT EXISTS hotel_clicks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        traveler_id TEXT,
        hotel_id TEXT,
        hotel_name TEXT,
        price REAL,
        score REAL,
        position INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    conn.commit()
    conn.close()


def save_trip(traveler_id: str, trip_dict: Dict[str, Any]):
    """Sauvegarde un voyage en base"""
    conn = get_db()
    conn.execute(
        """INSERT INTO trips (traveler_id, query, intent, context, recommendations) 
           VALUES (?, ?, ?, ?, ?)""",
        (
            traveler_id,
            trip_dict.get("raw_query", ""),
            json.dumps(trip_dict.get("intent", {})),
            json.dumps(trip_dict.get("context", {})),
            json.dumps(trip_dict.get("recommendations", []))
        )
    )
    conn.commit()
    conn.close()


def save_click(traveler_id: str, hotel_id: str, hotel_name: str, price: float, score: float, position: int):
    """Enregistre un clic sur un hôtel"""
    conn = get_db()
    
    # Mettre à jour le dernier voyage avec l'hôtel cliqué
    conn.execute(
        """UPDATE trips SET clicked_hotel_id = ? 
           WHERE traveler_id = ? AND id = (SELECT MAX(id) FROM trips WHERE traveler_id = ?)""",
        (hotel_id, traveler_id, traveler_id)
    )
    
    # Enregistrer le clic
    conn.execute(
        """INSERT INTO hotel_clicks (traveler_id, hotel_id, hotel_name, price, score, position) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        (traveler_id, hotel_id, hotel_name, price, score, position)
    )
    
    conn.commit()
    conn.close()


def get_traveler_history(traveler_id: str, limit: int = 20) -> List[Dict]:
    """Récupère l'historique des voyages d'un utilisateur"""
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM trips WHERE traveler_id = ? 
           ORDER BY created_at DESC LIMIT ?""",
        (traveler_id, limit)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# Initialiser la base au démarrage
init_db()
