"""
Database Engine — SQLite pour le MVP, PostgreSQL pour la prod.
"""

import sqlite3, json, os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stayo.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS travelers (
        id TEXT PRIMARY KEY, name TEXT, email TEXT,
        preferences TEXT DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        traveler_id TEXT, query TEXT, intent TEXT, context TEXT,
        recommendations TEXT, clicked_hotel_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS hotel_clicks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        traveler_id TEXT, hotel_id TEXT, hotel_name TEXT,
        price REAL, score REAL, position INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()


def save_trip(traveler_id: str, trip_dict: dict):
    conn = get_db()
    conn.execute("INSERT INTO trips (traveler_id, query, intent, context, recommendations) VALUES (?, ?, ?, ?, ?)",
        (traveler_id, trip_dict.get("raw_query", ""), json.dumps(trip_dict.get("intent", {})),
         json.dumps(trip_dict.get("context", {})), json.dumps(trip_dict.get("recommendations", []))))
    conn.commit()
    conn.close()


def save_click(traveler_id: str, hotel_id: str, hotel_name: str, price: float, score: float, position: int):
    conn = get_db()
    conn.execute("UPDATE trips SET clicked_hotel_id = ? WHERE traveler_id = ? AND id = (SELECT MAX(id) FROM trips WHERE traveler_id = ?)",
        (hotel_id, traveler_id, traveler_id))
    conn.execute("INSERT INTO hotel_clicks (traveler_id, hotel_id, hotel_name, price, score, position) VALUES (?, ?, ?, ?, ?, ?)",
        (traveler_id, hotel_id, hotel_name, price, score, position))
    conn.commit()
    conn.close()


def get_traveler_history(traveler_id: str, limit: int = 20) -> list:
    conn = get_db()
    rows = conn.execute("SELECT * FROM trips WHERE traveler_id = ? ORDER BY created_at DESC LIMIT ?",
        (traveler_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Init au démarrage
init_db()