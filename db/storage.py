"""
Historical Data Storage
========================
Bulk insert options snapshots and gamma levels into SQLite.
"""

from datetime import datetime
from logger import get_logger
from db.models import get_connection, init_db

log = get_logger("db.storage")


def save_snapshot(contracts: list, timestamp: str = None):
    """Bulk insert option contracts from a fetch cycle into the snapshots table.

    Args:
        contracts: List of contract dicts from fetch_option_data()
        timestamp: ISO timestamp for this snapshot (defaults to now)
    """
    if not contracts:
        return

    if timestamp is None:
        timestamp = datetime.now().isoformat()

    conn = get_connection()
    init_db()  # Ensure tables exist

    rows = []
    for c in contracts:
        ticker = c.get('Symbol', '')
        strike = c.get('Strike', 0) or 0
        spot = c.get('UnderlyingPrice', 0) or 0
        gamma = c.get('Gamma', 0) or 0
        oi = c.get('OpenInterest', 0) or 0
        vega = c.get('Vega', 0) or 0
        opt_type = c.get('Type', '')

        # Compute exposures
        gex = gamma * oi * 100 * spot
        if opt_type == 'PUT':
            gex = -gex
        vex = vega * oi * 100
        if opt_type == 'PUT':
            vex = -vex

        rows.append((
            timestamp,
            ticker,
            strike,
            c.get('Expiration', ''),
            opt_type,
            oi,
            c.get('Volume', 0) or 0,
            gamma,
            c.get('Delta', 0) or 0,
            vega,
            c.get('Theta', 0) or 0,
            spot,
            c.get('ImpliedVol', 0) or c.get('Volatility', 0) or 0,
            gex,
            vex,
        ))

    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO snapshots
            (timestamp, ticker, strike, expiration, option_type, oi, volume,
             gamma, delta, vega, theta, underlying_price, implied_vol, gex, vex)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

    conn.commit()
    conn.close()
    log.info("Saved %d contract snapshots to database", len(rows))


def save_gamma_snapshot(gamma_data: dict, timestamp: str = None):
    """Save computed gamma levels per ticker.

    Args:
        gamma_data: Dict from compute_star_levels() — { ticker: { price, max_positive_gamma_strike, ... } }
        timestamp: ISO timestamp (defaults to now)
    """
    if not gamma_data:
        return

    if timestamp is None:
        timestamp = datetime.now().isoformat()

    conn = get_connection()
    init_db()

    rows = []
    for ticker, data in gamma_data.items():
        # Compute net GEX for the ticker (sum all per-strike GEX)
        net_gex = (data.get('max_positive_gamma_value', 0) or 0) + (data.get('max_negative_gamma_value', 0) or 0)

        rows.append((
            timestamp,
            ticker,
            data.get('price', 0),
            data.get('max_positive_gamma_strike'),
            data.get('max_positive_gamma_value', 0),
            data.get('max_negative_gamma_strike'),
            data.get('max_negative_gamma_value', 0),
            net_gex,
        ))

    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO gamma_levels
            (timestamp, ticker, price, max_pos_strike, max_pos_gex,
             max_neg_strike, max_neg_gex, net_gex)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

    conn.commit()
    conn.close()
    log.info("Saved gamma levels for %d tickers", len(rows))


def save_alert(ticker: str, alert_type: str, message: str, details: str = None):
    """Save an alert event to the database."""
    conn = get_connection()
    init_db()

    timestamp = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO alert_history (timestamp, ticker, alert_type, message, details) VALUES (?, ?, ?, ?, ?)",
        (timestamp, ticker, alert_type, message, details)
    )
    conn.commit()
    conn.close()


def save_recommendation_log(recommendations: list, timestamp: str = None):
    """Log recommendations for backtesting.

    Args:
        recommendations: List of Recommendation dicts with ticker, score, direction, play_type, price
        timestamp: ISO timestamp (defaults to now)
    """
    if not recommendations:
        return

    if timestamp is None:
        timestamp = datetime.now().isoformat()

    conn = get_connection()
    init_db()

    rows = []
    for r in recommendations:
        rows.append((
            timestamp,
            r.get('ticker', ''),
            r.get('score', 0),
            r.get('direction', ''),
            r.get('play_type', ''),
            r.get('price_at_score', 0),
            r.get('net_gex', 0),
            r.get('iv_rank', 0),
        ))

    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO recommendation_log
            (timestamp, ticker, score, direction, play_type,
             price_at_score, net_gex, iv_rank)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

    conn.commit()
    conn.close()
    log.info("Logged %d recommendations for backtesting", len(rows))


def prune_old_data(retention_days: int = None):
    """Delete data older than retention period."""
    if retention_days is None:
        try:
            from config import load_config
            retention_days = load_config().database.retention_days
        except Exception:
            retention_days = 30

    conn = get_connection()
    cursor = conn.cursor()

    cutoff = datetime.now().timestamp() - (retention_days * 86400)
    cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()

    cursor.execute("DELETE FROM snapshots WHERE timestamp < ?", (cutoff_iso,))
    deleted_snapshots = cursor.rowcount

    cursor.execute("DELETE FROM gamma_levels WHERE timestamp < ?", (cutoff_iso,))
    deleted_gamma = cursor.rowcount

    cursor.execute("DELETE FROM alert_history WHERE timestamp < ?", (cutoff_iso,))
    deleted_alerts = cursor.rowcount

    conn.commit()
    conn.close()

    log.info(
        "Pruned old data (>%d days): %d snapshots, %d gamma_levels, %d alerts",
        retention_days, deleted_snapshots, deleted_gamma, deleted_alerts
    )
