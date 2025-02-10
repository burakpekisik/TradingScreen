import sqlite3
from datetime import datetime
import pandas as pd


def init_db():
    conn = sqlite3.connect("trading.db")
    c = conn.cursor()

    # Users table
    c.execute(
        """CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY,
                  username TEXT UNIQUE,
                  balance REAL)"""
    )

    # Assets table
    c.execute(
        """CREATE TABLE IF NOT EXISTS assets
                 (id INTEGER PRIMARY KEY,
                  user_id INTEGER,
                  symbol TEXT,
                  quantity REAL,
                  avg_price REAL,
                  total_cost REAL,
                  market TEXT,
                  FOREIGN KEY (user_id) REFERENCES users(id))"""
    )

    # Transactions table
    c.execute(
        """CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY,
                  user_id INTEGER,
                  symbol TEXT,
                  type TEXT,
                  quantity REAL,
                  price REAL,
                  total_amount REAL,
                  profit_loss REAL,
                  timestamp DATETIME,
                  chart_timestamp DATETIME,
                  market TEXT,
                  FOREIGN KEY (user_id) REFERENCES users(id))"""
    )

    conn.commit()
    conn.close()


def init_user(user_id, initial_balance=10000):
    """Initialize user with given balance if not exists"""
    conn = sqlite3.connect("trading.db")
    c = conn.cursor()
    
    c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (id, username, balance) VALUES (?, ?, ?)",
            (user_id, f"user_{user_id}", initial_balance)
        )
        conn.commit()
    conn.close()


def get_user_balance(user_id):
    conn = sqlite3.connect("trading.db")
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    balance = c.fetchone()[0]
    conn.close()
    return balance


def update_user_balance(user_id, new_balance):
    conn = sqlite3.connect("trading.db")
    c = conn.cursor()
    c.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
    conn.commit()
    conn.close()


def add_transaction(
    user_id,
    symbol,
    type,
    quantity,
    price,
    total_amount,
    profit_loss,
    market,
    chart_timestamp,
):
    conn = sqlite3.connect("trading.db")
    c = conn.cursor()
    timestamp = datetime.now()

    # Pandas Timestamp'i datetime'a çevir
    if isinstance(chart_timestamp, pd.Timestamp):
        chart_timestamp = chart_timestamp.to_pydatetime()

    c.execute(
        """INSERT INTO transactions 
                 (user_id, symbol, type, quantity, price, total_amount, profit_loss, timestamp, chart_timestamp, market)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            symbol,
            type,
            quantity,
            price,
            total_amount,
            profit_loss,
            timestamp,
            chart_timestamp,
            market,
        ),
    )
    conn.commit()
    conn.close()


def update_asset(user_id, symbol, quantity, avg_price, total_cost, market):
    conn = sqlite3.connect("trading.db")
    c = conn.cursor()

    # Önce eski kaydı sil
    c.execute(
        """DELETE FROM assets 
                 WHERE user_id = ? AND symbol = ? AND market = ?""",
        (user_id, symbol, market),
    )

    # Eğer quantity 0'dan büyükse yeni kaydı ekle
    if quantity > 0:
        c.execute(
            """INSERT INTO assets 
                     (user_id, symbol, quantity, avg_price, total_cost, market)
                     VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, symbol, quantity, avg_price, total_cost, market),
        )

    conn.commit()
    conn.close()
