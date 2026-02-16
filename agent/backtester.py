"""
Backtester for Trade Recommendations
=======================================
Compares past recommendations against actual price outcomes.
All data sourced exclusively from Schwab API data stored in the historical DB.

Usage:
    from agent.backtester import evaluate_recommendations
    results = evaluate_recommendations(hours=24)
"""

from typing import Dict, List
from logger import get_logger

log = get_logger("agent.backtester")


def evaluate_recommendations(hours: int = 24) -> Dict:
    """Evaluate past recommendation outcomes.

    Pulls recommendation_log and compares price_at_score to current
    prices from gamma_levels (all Schwab-sourced data).

    Returns:
        {
            'total_recommendations': int,
            'accuracy': { 'bullish_correct': %, 'bearish_correct': %, 'overall': % },
            'by_score_tier': { '80-100': {...}, '60-79': {...}, ... },
            'outcomes': [ list of individual outcomes ]
        }
    """
    try:
        from db.queries import get_recommendation_outcomes
        outcomes = get_recommendation_outcomes(hours=hours)
    except Exception as e:
        log.warning("Cannot run backtest: %s", e)
        return {'error': str(e), 'total_recommendations': 0}

    if not outcomes:
        return {
            'total_recommendations': 0,
            'message': 'No recommendation data yet. Run the fetcher to generate history.',
            'accuracy': {},
            'by_score_tier': {},
            'outcomes': [],
        }

    # Analyze outcomes
    bullish_correct = 0
    bullish_total = 0
    bearish_correct = 0
    bearish_total = 0
    neutral_total = 0

    tiers = {
        '80-100': {'count': 0, 'correct': 0, 'avg_return': 0, 'returns': []},
        '60-79':  {'count': 0, 'correct': 0, 'avg_return': 0, 'returns': []},
        '40-59':  {'count': 0, 'correct': 0, 'avg_return': 0, 'returns': []},
        '0-39':   {'count': 0, 'correct': 0, 'avg_return': 0, 'returns': []},
    }

    for o in outcomes:
        score = o.get('score', 0)
        direction = o.get('direction', '')
        ret = o.get('return_pct', 0)

        # Determine tier
        if score >= 80:
            tier = '80-100'
        elif score >= 60:
            tier = '60-79'
        elif score >= 40:
            tier = '40-59'
        else:
            tier = '0-39'

        tiers[tier]['count'] += 1
        tiers[tier]['returns'].append(ret)

        # Check direction accuracy
        if direction == 'BULLISH':
            bullish_total += 1
            if ret > 0:
                bullish_correct += 1
                tiers[tier]['correct'] += 1
        elif direction == 'BEARISH':
            bearish_total += 1
            if ret < 0:
                bearish_correct += 1
                tiers[tier]['correct'] += 1
        else:
            neutral_total += 1
            if abs(ret) < 0.5:  # Neutral = price didn't move much
                tiers[tier]['correct'] += 1

    # Compute tier averages
    for tier_name, t in tiers.items():
        if t['returns']:
            t['avg_return'] = round(sum(t['returns']) / len(t['returns']), 3)
            t['hit_rate'] = round(t['correct'] / t['count'] * 100, 1) if t['count'] > 0 else 0
        del t['returns']  # Don't include raw list in output

    # Overall accuracy
    total_directional = bullish_total + bearish_total
    total_correct = bullish_correct + bearish_correct

    result = {
        'total_recommendations': len(outcomes),
        'lookback_hours': hours,
        'accuracy': {
            'bullish_hit_rate': round(bullish_correct / bullish_total * 100, 1) if bullish_total > 0 else 0,
            'bearish_hit_rate': round(bearish_correct / bearish_total * 100, 1) if bearish_total > 0 else 0,
            'overall_hit_rate': round(total_correct / total_directional * 100, 1) if total_directional > 0 else 0,
            'bullish_total': bullish_total,
            'bearish_total': bearish_total,
            'neutral_total': neutral_total,
        },
        'by_score_tier': tiers,
        'outcomes': outcomes[:50],  # Cap output
    }

    log.info("Backtest: %d recs, overall hit rate: %.1f%%",
             len(outcomes), result['accuracy']['overall_hit_rate'])

    return result
