"""
Strategy Mapper
================
Maps combinations of scoring signals to suggested option play types.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class StrategyRecommendation:
    """A suggested options strategy based on signal analysis."""
    play_type: str        # "Call Spread", "Put Spread", "Iron Condor", etc.
    direction: str        # "BULLISH", "BEARISH", "NEUTRAL"
    description: str      # One-liner explaining the play
    risk_profile: str     # "Defined Risk", "Undefined Risk"


# Strategy lookup: keyed by (gex_regime, wall_position, skew_direction)
# gex_regime: "positive" (mean-revert) or "negative" (trend)
# wall_position: "near_call_wall", "near_put_wall", "mid_range"
# skew_direction: "bullish", "bearish", "neutral"

STRATEGY_MAP = {
    # === POSITIVE GEX (Mean-Reversion Regime — Sell Premium) ===
    ("positive", "near_call_wall", "bullish"):   StrategyRecommendation(
        "Bear Call Spread", "BEARISH",
        "Price at call wall resistance in mean-reversion regime — fade the rally",
        "Defined Risk"),
    ("positive", "near_call_wall", "bearish"):   StrategyRecommendation(
        "Bear Call Spread", "BEARISH",
        "Bearish skew + call wall resistance — high-probability fade",
        "Defined Risk"),
    ("positive", "near_call_wall", "neutral"):   StrategyRecommendation(
        "Iron Condor", "NEUTRAL",
        "Neutral skew at resistance — sell both sides, gamma supports range",
        "Defined Risk"),

    ("positive", "near_put_wall", "bullish"):    StrategyRecommendation(
        "Bull Call Spread", "BULLISH",
        "Bullish skew at put wall support — buy the bounce",
        "Defined Risk"),
    ("positive", "near_put_wall", "bearish"):    StrategyRecommendation(
        "Bull Put Spread", "BULLISH",
        "Put wall support in positive GEX — sell puts for premium with floor",
        "Defined Risk"),
    ("positive", "near_put_wall", "neutral"):    StrategyRecommendation(
        "Bull Put Spread", "BULLISH",
        "Support level in mean-reversion — sell premium into support",
        "Defined Risk"),

    ("positive", "mid_range", "bullish"):        StrategyRecommendation(
        "Iron Condor", "NEUTRAL",
        "Positive GEX mid-range — range-bound, sell premium both sides",
        "Defined Risk"),
    ("positive", "mid_range", "bearish"):        StrategyRecommendation(
        "Iron Condor", "NEUTRAL",
        "Positive GEX keeps price pinned — sell premium into the range",
        "Defined Risk"),
    ("positive", "mid_range", "neutral"):        StrategyRecommendation(
        "Iron Condor", "NEUTRAL",
        "Perfect mean-reversion setup — sell iron condor around current price",
        "Defined Risk"),

    # === NEGATIVE GEX (Trending Regime — Buy Directional) ===
    ("negative", "near_call_wall", "bullish"):   StrategyRecommendation(
        "Bull Call Spread", "BULLISH",
        "Negative GEX + bullish flow + near resistance — breakout potential",
        "Defined Risk"),
    ("negative", "near_call_wall", "bearish"):   StrategyRecommendation(
        "Bear Put Spread", "BEARISH",
        "Bearish skew at resistance in volatile regime — rejection likely",
        "Defined Risk"),
    ("negative", "near_call_wall", "neutral"):   StrategyRecommendation(
        "Long Straddle", "NEUTRAL",
        "Negative GEX at key level — expect big move in either direction",
        "Defined Risk"),

    ("negative", "near_put_wall", "bullish"):    StrategyRecommendation(
        "Bull Call Spread", "BULLISH",
        "Bullish positioning at put support in trend regime — bounce play",
        "Defined Risk"),
    ("negative", "near_put_wall", "bearish"):    StrategyRecommendation(
        "Bear Put Spread", "BEARISH",
        "Negative GEX + bearish flow at put wall — breakdown expected",
        "Defined Risk"),
    ("negative", "near_put_wall", "neutral"):    StrategyRecommendation(
        "Long Straddle", "NEUTRAL",
        "Negative GEX at support — breakout or bounce, buy both sides",
        "Defined Risk"),

    ("negative", "mid_range", "bullish"):        StrategyRecommendation(
        "Bull Call Spread", "BULLISH",
        "Negative GEX trend regime + bullish skew — ride the momentum up",
        "Defined Risk"),
    ("negative", "mid_range", "bearish"):        StrategyRecommendation(
        "Bear Put Spread", "BEARISH",
        "Negative GEX + bearish skew — ride the momentum down",
        "Defined Risk"),
    ("negative", "mid_range", "neutral"):        StrategyRecommendation(
        "Long Straddle", "NEUTRAL",
        "High volatility regime with no directional conviction — play the vol",
        "Defined Risk"),
}


def get_strategy(gex_regime: str, wall_position: str, skew_direction: str) -> StrategyRecommendation:
    """Look up the recommended strategy for a signal combination.

    Args:
        gex_regime: "positive" or "negative"
        wall_position: "near_call_wall", "near_put_wall", or "mid_range"
        skew_direction: "bullish", "bearish", or "neutral"

    Returns:
        StrategyRecommendation with play type, direction, and description
    """
    key = (gex_regime, wall_position, skew_direction)
    strategy = STRATEGY_MAP.get(key)

    if strategy is None:
        # Fallback: if no exact match, return a neutral play
        return StrategyRecommendation(
            "Iron Condor", "NEUTRAL",
            "Insufficient signal clarity — consider neutral premium selling",
            "Defined Risk"
        )

    return strategy
