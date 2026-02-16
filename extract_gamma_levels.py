"""
Extract Gamma Levels
====================
Parses option_data.js to compute net GEX (Gamma Exposure) per strike for each ticker.
Uses the same per-cell (strike × expiration) formula as the heatmap dashboard so that
the star levels match the ⭐ (max +GEX) and ★ (max -GEX) indicators.

Outputs:
  1. gamma_levels.json - Highest positive/negative gamma strikes per ticker
"""

import json
import re
import os


def load_option_data(filepath='option_data.js'):
    """Load and parse option_data.js into a Python list of contracts."""
    print(f"Loading {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract JSON array from JS: const OPTION_DATA = [...];
    match = re.search(r'const OPTION_DATA\s*=\s*(\[.*\])\s*;', content, re.DOTALL)
    if not match:
        raise ValueError("Could not find OPTION_DATA in option_data.js")

    data = json.loads(match.group(1))
    print(f"  Loaded {len(data):,} contracts")
    return data


def compute_star_levels(contracts):
    """
    Compute the star-level gamma strikes for each ticker using the SAME
    per-cell (strike × expiration) logic as the heatmap dashboard.

    Heatmap formula: GEX = Gamma × OI × 100 × SpotPrice² × 0.01
    Net per cell = sum of (calls positive, puts negative) at that (strike, exp).
    Stars mark the single cell with the highest positive and most negative value.

    Returns dict: { ticker: { price, max_positive_gamma_strike, max_negative_gamma_strike, ... } }
    """
    # Group contracts by ticker
    by_ticker = {}
    ticker_prices = {}

    for c in contracts:
        ticker = c.get('Symbol', '')
        if not ticker:
            continue

        spot = c.get('UnderlyingPrice', 0) or 0
        if spot == 0:
            continue

        if ticker not in by_ticker:
            by_ticker[ticker] = []
            ticker_prices[ticker] = spot
        by_ticker[ticker].append(c)

    results = {}

    for ticker, ticker_contracts in by_ticker.items():
        spot = ticker_prices[ticker]

        # Build per-cell (strike, expiration) net GEX — same as heatmap
        cell_gex = {}  # (strike, exp) -> net GEX

        for c in ticker_contracts:
            strike = c.get('Strike', 0)
            exp = c.get('Expiration', '')
            gamma = c.get('Gamma', 0) or 0
            oi = c.get('OpenInterest', 0) or 0
            opt_type = c.get('Type', '')

            if strike == 0:
                continue

            # Heatmap formula: GEX = Gamma × OI × 100 × SpotPrice² × 0.01
            exposure = gamma * oi * 100 * spot * spot * 0.01

            # Calls positive, puts negative
            if opt_type == 'CALL':
                net = exposure
            elif opt_type == 'PUT':
                net = -exposure
            else:
                continue

            key = (strike, exp)
            if key not in cell_gex:
                cell_gex[key] = 0
            cell_gex[key] += net

        # Find the cell with max positive and max negative GEX (the stars)
        max_pos_strike = None
        max_pos_gex = -float('inf')
        max_neg_strike = None
        max_neg_gex = float('inf')

        for (strike, exp), gex in cell_gex.items():
            if gex > 0 and gex > max_pos_gex:
                max_pos_gex = gex
                max_pos_strike = strike
            if gex < 0 and gex < max_neg_gex:
                max_neg_gex = gex
                max_neg_strike = strike

        results[ticker] = {
            'price': spot,
            'max_positive_gamma_strike': max_pos_strike,
            'max_positive_gamma_value': max_pos_gex if max_pos_strike else 0,
            'max_negative_gamma_strike': max_neg_strike,
            'max_negative_gamma_value': max_neg_gex if max_neg_strike else 0,
        }

    return results


def run_extraction():
    """Run the full extraction pipeline. Can be called from continuous_fetcher."""
    print("=" * 70)
    print("GAMMA STAR LEVEL EXTRACTOR")
    print("=" * 70)

    # Step 1: Load raw option data
    contracts = load_option_data('option_data.js')

    # Step 2: Compute star-level strikes per ticker (matches heatmap logic)
    print("\nComputing per-cell GEX to find star levels...")
    gamma_data = compute_star_levels(contracts)
    print(f"  Processed {len(gamma_data)} tickers")

    # Print summary
    print(f"\n{'Ticker':<8} {'Price':>10} {'* +GEX Strike':>16} {'* -GEX Strike':>16}")
    print("-" * 54)
    for ticker in sorted(gamma_data.keys()):
        d = gamma_data[ticker]
        pos = f"${d['max_positive_gamma_strike']:.1f}" if d['max_positive_gamma_strike'] else "N/A"
        neg = f"${d['max_negative_gamma_strike']:.1f}" if d['max_negative_gamma_strike'] else "N/A"
        print(f"{ticker:<8} ${d['price']:>9.2f} {pos:>16} {neg:>16}")

    # Step 3: Save JSON
    print("\nSaving gamma_levels.json...")
    with open('gamma_levels.json', 'w', encoding='utf-8') as f:
        json.dump(gamma_data, f, indent=2)
    print(f"  Saved gamma_levels.json ({len(gamma_data)} tickers)")

    print("\n" + "=" * 70)
    print("DONE! gamma_levels.json updated.")
    print("=" * 70)

    return gamma_data


def main():
    run_extraction()


if __name__ == '__main__':
    main()
