import sqlite3
from datetime import datetime, timedelta

# ============ DATABASE ============
def init_db():
    conn = sqlite3.connect("subscribers.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscribers (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        plan TEXT,
        expires_at TEXT,
        is_active INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        payment_id TEXT PRIMARY KEY,
        user_id INTEGER,
        amount INTEGER,
        plan TEXT,
        status TEXT,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()

def get_subscriber(user_id):
    conn = sqlite3.connect("subscribers.db")
    c = conn.cursor()
    c.execute("SELECT * FROM subscribers WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def add_subscriber(user_id, username, full_name, plan, days):
    expires_at = (datetime.now() + timedelta(days=days)).isoformat()
    conn = sqlite3.connect("subscribers.db")
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO subscribers 
                (user_id, username, full_name, plan, expires_at, is_active)
                VALUES (?, ?, ?, ?, ?, 1)''',
              (user_id, username, full_name, plan, expires_at))
    conn.commit()
    conn.close()

def add_payment(payment_id, user_id, amount, plan, status, created_at):
    conn = sqlite3.connect("subscribers.db")
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO payments
                (payment_id, user_id, amount, plan, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)''',
              (payment_id, user_id, amount, plan, status, created_at))
    conn.commit()
    conn.close()
