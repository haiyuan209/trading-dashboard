"""
Database Schema & Initialization
==================================
SQLite tables for storing historical options snapshots and gamma levels.
"""

import sqlite3
import os
from logger import get_logger

log = get_logger("db.models")


def get_db_path() -> str:
    """Get database path from config."""
    try:
        from config import load_config
        return load_config().database.path
    except Exception:
        return "data/options_history.db"


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """Get a database connection, creating the directory if needed."""
    if db_path is None:
        db_path = get_db_path()

    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent read performance
    return conn


def init_db(db_path: str = None):
    """Create all tables if they don't exist."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Snapshots table — stores per-contract data each fetch cycle
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ticker TEXT NOT NULL,
            strike REAL NOT NULL,
            expiration TEXT,
            option_type TEXT,
            oi INTEGER DEFAULT 0,
            volume INTEGER DEFAULT 0,
            gamma REAL DEFAULT 0,
            delta REAL DEFAULT 0,
            vega REAL DEFAULT 0,
            theta REAL DEFAULT 0,
            underlying_price REAL DEFAULT 0,
            implied_vol REAL DEFAULT 0,
            gex REAL DEFAULT 0,
            vex REAL DEFAULT 0
        )
    """)

    # Gamma levels table — stores computed star levels per ticker per cycle
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gamma_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ticker TEXT NOT NULL,
            price REAL DEFAULT 0,
            max_pos_strike REAL,
            max_pos_gex REAL,
            max_neg_strike REAL,
            max_neg_gex REAL,
            net_gex REAL DEFAULT 0
        )
    """)

    # Alerts history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ticker TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            details TEXT
        )
    """)

    # Indices for efficient time-series queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_snapshots_ticker_ts
        ON snapshots(ticker, timestamp)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_snapshots_ticker_strike_ts
        ON snapshots(ticker, strike, timestamp)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_gamma_levels_ticker_ts
        ON gamma_levels(ticker, timestamp)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alerts_ts
        ON alert_history(timestamp)
    """)

    # Recommendation log for backtesting
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ticker TEXT NOT NULL,
            score INTEGER NOT NULL,
            direction TEXT NOT NULL,
            play_type TEXT NOT NULL,
            price_at_score REAL DEFAULT 0,
            net_gex REAL DEFAULT 0,
            iv_rank REAL DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_rec_log_ticker_ts
        ON recommendation_log(ticker, timestamp)
    """)

    conn.commit()
    conn.close()
    log.info("Database initialized at %s", db_path or get_db_path())
