"""
Historical Data Queries
========================
Query functions for time-series analysis of stored options data.
"""

from datetime import datetime, timedelta
from db.models import get_connection, init_db
from logger import get_logger

log = get_logger("db.queries")


def get_oi_change(ticker: str, strike: float = None, interval_minutes: int = 60) -> list:
    """Get OI change for a ticker (optionally at a specific strike) over time interval.

    Returns list of dicts: [{ strike, old_oi, new_oi, oi_change, pct_change }, ...]
    """
    conn = get_connection()
    now = datetime.now()
    cutoff = (now - timedelta(minutes=interval_minutes)).isoformat()
    now_iso = now.isoformat()

    query = """
        WITH latest AS (
            SELECT ticker, strike, oi, timestamp,
                   ROW_NUMBER() OVER (PARTITION BY ticker, strike ORDER BY timestamp DESC) as rn
            FROM snapshots
            WHERE ticker = ? AND timestamp >= ?
        ),
        earliest AS (
            SELECT ticker, strike, oi, timestamp,
                   ROW_NUMBER() OVER (PARTITION BY ticker, strike ORDER BY timestamp ASC) as rn
            FROM snapshots
            WHERE ticker = ? AND timestamp >= ?
        )
        SELECT
            l.strike,
            e.oi as old_oi,
            l.oi as new_oi,
            (l.oi - e.oi) as oi_change,
            CASE WHEN e.oi > 0 THEN ROUND((l.oi - e.oi) * 100.0 / e.oi, 2) ELSE 0 END as pct_change
        FROM latest l
        JOIN earliest e ON l.ticker = e.ticker AND l.strike = e.strike
        WHERE l.rn = 1 AND e.rn = 1
    """
    params = [ticker, cutoff, ticker, cutoff]

    if strike is not None:
        query += " AND l.strike = ?"
        params.append(strike)

    query += " ORDER BY ABS(oi_change) DESC"

    cursor = conn.cursor()
    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return results


def get_gamma_history(ticker: str, hours: int = 24) -> list:
    """Get gamma level time series for a ticker.

    Returns list of dicts: [{ timestamp, price, max_pos_strike, max_neg_strike, net_gex }, ...]
    """
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, price, max_pos_strike, max_pos_gex,
               max_neg_strike, max_neg_gex, net_gex
        FROM gamma_levels
        WHERE ticker = ? AND timestamp >= ?
        ORDER BY timestamp ASC
    """, (ticker, cutoff))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_gex_flip_events(ticker: str, hours: int = 24) -> list:
    """Find timestamps where net GEX changed sign for a ticker.

    Returns list of dicts: [{ timestamp, old_gex, new_gex, direction }, ...]
    """
    history = get_gamma_history(ticker, hours)
    if len(history) < 2:
        return []

    flips = []
    for i in range(1, len(history)):
        old_gex = history[i - 1].get('net_gex', 0)
        new_gex = history[i].get('net_gex', 0)

        if (old_gex > 0 and new_gex < 0) or (old_gex < 0 and new_gex > 0):
            direction = "positive_to_negative" if old_gex > 0 else "negative_to_positive"
            flips.append({
                'timestamp': history[i]['timestamp'],
                'old_gex': old_gex,
                'new_gex': new_gex,
                'direction': direction,
            })

    return flips


def get_latest_gamma_levels() -> dict:
    """Get the most recent gamma levels for all tickers.

    Returns dict: { ticker: { price, max_pos_strike, max_neg_strike, ... } }
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ticker, price, max_pos_strike, max_pos_gex,
               max_neg_strike, max_neg_gex, net_gex, timestamp
        FROM gamma_levels
        WHERE (ticker, timestamp) IN (
            SELECT ticker, MAX(timestamp) FROM gamma_levels GROUP BY ticker
        )
    """)

    results = {}
    for row in cursor.fetchall():
        row_dict = dict(row)
        ticker = row_dict.pop('ticker')
        results[ticker] = row_dict

    conn.close()
    return results


def get_recent_alerts(hours: int = 24, limit: int = 50) -> list:
    """Get recent alerts from the database."""
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, ticker, alert_type, message, details
        FROM alert_history
        WHERE timestamp >= ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (cutoff, limit))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_latest_snapshot_time() -> str:
    """Get the timestamp of the most recent snapshot."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(timestamp) as latest FROM snapshots")
    row = cursor.fetchone()
    conn.close()
    return row['latest'] if row and row['latest'] else None


def get_historical_percentile(ticker: str, field: str, current_value: float, hours: int = 168) -> float:
    """Rank a current value against the ticker's own historical range.

    Uses real Schwab data stored in gamma_levels table.

    Args:
        ticker: Symbol
        field: Column name in gamma_levels (e.g. 'net_gex')
        current_value: The value to rank
        hours: Lookback window (default: 7 days)

    Returns:
        Percentile as 0.0–1.0 (1.0 = highest ever in window)
    """
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

    # Validate field name to prevent injection
    allowed = {'net_gex', 'max_pos_gex', 'max_neg_gex', 'price'}
    if field not in allowed:
        conn.close()
        return 0.5  # neutral default

    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT {field} FROM gamma_levels
        WHERE ticker = ? AND timestamp >= ? AND {field} IS NOT NULL
        ORDER BY {field} ASC
    """, (ticker, cutoff))

    values = [row[field] for row in cursor.fetchall()]
    conn.close()

    if len(values) < 3:
        return 0.5  # not enough history — return neutral

    # Compute percentile rank
    count_below = sum(1 for v in values if v < current_value)
    percentile = count_below / len(values)
    return round(percentile, 3)


def get_signal_momentum(ticker: str, hours: int = 4) -> dict:
    """Get trend of net GEX over recent history.

    Uses real Schwab data stored in gamma_levels table.

    Returns:
        { 'gex_trend': float (-1 to 1), 'gex_samples': int,
          'gex_start': float, 'gex_end': float }
    """
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

    cursor = conn.cursor()
    cursor.execute("""
        SELECT net_gex, timestamp FROM gamma_levels
        WHERE ticker = ? AND timestamp >= ?
        ORDER BY timestamp ASC
    """, (ticker, cutoff))

    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if len(rows) < 2:
        return {'gex_trend': 0.0, 'gex_samples': len(rows),
                'gex_start': 0, 'gex_end': 0}

    gex_start = rows[0].get('net_gex', 0) or 0
    gex_end = rows[-1].get('net_gex', 0) or 0

    # Normalize trend to -1..1 range
    if gex_start == 0:
        gex_trend = 1.0 if gex_end > 0 else -1.0 if gex_end < 0 else 0.0
    else:
        change_pct = (gex_end - gex_start) / abs(gex_start)
        gex_trend = max(-1.0, min(1.0, change_pct))

    return {
        'gex_trend': round(gex_trend, 3),
        'gex_samples': len(rows),
        'gex_start': gex_start,
        'gex_end': gex_end,
    }


def get_iv_percentile(ticker: str, hours: int = 168) -> float:
    """Compute IV rank: where current avg IV sits vs its historical range.

    Uses real Schwab implied volatility data stored in snapshots.

    Returns:
        IV rank as 0.0–1.0 (1.0 = IV at highest point in lookback)
    """
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

    cursor = conn.cursor()

    # Get average IV per snapshot timestamp (only ATM-ish strikes)
    cursor.execute("""
        SELECT timestamp,
               AVG(implied_vol) as avg_iv
        FROM snapshots
        WHERE ticker = ? AND timestamp >= ?
              AND implied_vol > 0
              AND ABS(strike - underlying_price) / underlying_price < 0.05
        GROUP BY timestamp
        ORDER BY timestamp ASC
    """, (ticker, cutoff))

    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if len(rows) < 3:
        return 0.5  # not enough history

    iv_values = [r['avg_iv'] for r in rows if r['avg_iv']]
    if not iv_values:
        return 0.5

    current_iv = iv_values[-1]
    iv_min = min(iv_values)
    iv_max = max(iv_values)

    if iv_max == iv_min:
        return 0.5

    iv_rank = (current_iv - iv_min) / (iv_max - iv_min)
    return round(max(0.0, min(1.0, iv_rank)), 3)


def get_recommendation_outcomes(hours: int = 24) -> list:
    """Get past recommendations and compare price_at_score to current prices.

    Uses real Schwab data only. Joins recommendation_log with latest gamma_levels
    to get current price.

    Returns:
        List of dicts: [{ ticker, score, direction, price_at_score,
                          current_price, return_pct, timestamp }, ...]
    """
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.ticker, r.score, r.direction, r.play_type,
               r.price_at_score, r.timestamp,
               g.price as current_price
        FROM recommendation_log r
        LEFT JOIN (
            SELECT ticker, price, MAX(timestamp) as latest_ts
            FROM gamma_levels
            GROUP BY ticker
        ) g ON r.ticker = g.ticker
        WHERE r.timestamp >= ? AND r.price_at_score > 0
        ORDER BY r.timestamp DESC
    """, (cutoff,))

    results = []
    for row in cursor.fetchall():
        r = dict(row)
        current_price = r.get('current_price', 0) or 0
        price_at_score = r.get('price_at_score', 0)
        if price_at_score > 0 and current_price > 0:
            r['return_pct'] = round((current_price - price_at_score) / price_at_score * 100, 3)
        else:
            r['return_pct'] = 0
        results.append(r)

    conn.close()
    return results

