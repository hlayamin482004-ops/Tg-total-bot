import sqlite3
import os

DB_PATH = "ledger.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        agent TEXT DEFAULT NULL,
        total_bet INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS pending_bets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        bet_text TEXT,
        calculated_amount INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, agent, total_bet FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "username": row[1], "agent": row[2], "total_bet": row[3]}
    return None

def create_user(user_id, username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO users (user_id, username, agent, total_bet) VALUES (?, ?, ?, ?)",
              (user_id, username, None, 0))
    conn.commit()
    conn.close()

def update_total(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET total_bet = total_bet + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def set_agent(user_id, agent):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET agent = ? WHERE user_id = ?", (agent, user_id))
    conn.commit()
    conn.close()
    
    # Agent ရှိလာပြီဆို pending bets တွေ ပြန်တွက်
    c.execute("SELECT id, calculated_amount FROM pending_bets WHERE user_id = ?", (user_id,))
    pending = c.fetchall()
    for p in pending:
        update_total(user_id, p[1])
        c.execute("DELETE FROM pending_bets WHERE id = ?", (p[0],))
    conn.commit()
    conn.close()

def add_pending_bet(user_id, bet_text, calculated_amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO pending_bets (user_id, bet_text, calculated_amount) VALUES (?, ?, ?)",
              (user_id, bet_text, calculated_amount))
    conn.commit()
    conn.close()

def get_pending_bets(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT bet_text, calculated_amount FROM pending_bets WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def has_agent(user_id):
    user = get_user(user_id)
    return user and user['agent'] is not None
