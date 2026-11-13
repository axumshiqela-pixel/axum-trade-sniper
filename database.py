import os
import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
else:
    import sqlite3

def get_conn():
    if USE_POSTGRES:
        url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(url)
    else:
        return sqlite3.connect("axum.db")

def init_db():
    conn = get_conn()
    c = conn.cursor()
    # Users table
    if USE_POSTGRES:
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (telegram_id BIGINT PRIMARY KEY, username TEXT, expiry TEXT, tier TEXT)''')
        # Used Receipts table (To prevent reused TRX)
        c.execute('''CREATE TABLE IF NOT EXISTS used_receipts
                     (trx_id TEXT PRIMARY KEY, telegram_id BIGINT, used_at TEXT)''')
    else:
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (telegram_id INTEGER PRIMARY KEY, username TEXT, expiry TEXT, tier TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS used_receipts
                     (trx_id TEXT PRIMARY KEY, telegram_id INTEGER, used_at TEXT)''')
    conn.commit()
    conn.close()

def add_user(telegram_id, username, expiry, tier):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("INSERT INTO users (telegram_id, username, expiry, tier) VALUES (%s, %s, %s, %s) ON CONFLICT (telegram_id) DO UPDATE SET username=EXCLUDED.username, expiry=EXCLUDED.expiry, tier=EXCLUDED.tier",
                  (telegram_id, username, expiry, tier))
    else:
        c.execute("INSERT OR REPLACE INTO users (telegram_id, username, expiry, tier) VALUES (?, ?, ?, ?)",
                  (telegram_id, username, expiry, tier))
    conn.commit()
    conn.close()

def get_user(telegram_id):
    conn = get_conn()
    if USE_POSTGRES:
        c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
        row = c.fetchone()
        conn.close()
        return row
    else:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return {"telegram_id": row[0], "username": row[1], "expiry": row[2], "tier": row[3]}
        return None

# --- NEW FUNCTIONS FOR RECEIPT CHECKING ---

def is_receipt_used(trx_id):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT trx_id FROM used_receipts WHERE trx_id = %s", (trx_id,))
    else:
        c.execute("SELECT trx_id FROM used_receipts WHERE trx_id = ?", (trx_id,))
    row = c.fetchone()
    conn.close()
    return row is not None

def save_used_receipt(trx_id, telegram_id):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if USE_POSTGRES:
        c.execute("INSERT INTO used_receipts (trx_id, telegram_id, used_at) VALUES (%s, %s, %s)", (trx_id, telegram_id, now))
    else:
        c.execute("INSERT INTO used_receipts (trx_id, telegram_id, used_at) VALUES (?, ?, ?)", (trx_id, telegram_id, now))
    conn.commit()
    conn.close()

# Add dummy history function back so server.py doesn't crash
def get_recent_signals(limit=10):
    return [] 
