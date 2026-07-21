# analysis/smart_money_engine.py

from analysis.market_structure import analyze_market_structure
from analysis.volume import analyze_volume
from analysis.liquidity import analyze_liquidity


def analyze_smart_money(df):
    """
    Smart Money Analysis

    Returns:
    {
        score,
        reasons,
        structure,
        volume,
        liquidity
    }
    """

    if df.empty or len(df) < 200:
        return {
            "score": 0,
            "reasons": ["Not enough historical data"],
            "structure": {},
            "volume": {},
            "liquidity": {},
        }

    score = 0
    reasons = []

    # -----------------------------
    # Market Structure
    # -----------------------------
    structure = analyze_market_structure(df)

    score += structure.get("score", 0)
    reasons.extend(structure.get("reasons", []))

    # -----------------------------
    # Volume Analysis
    # -----------------------------
    volume = analyze_volume(df)

    score += volume.get("score", 0)
    reasons.extend(volume.get("reasons", []))

    # -----------------------------
    # Liquidity Analysis
    # -----------------------------
    liquidity = analyze_liquidity(df)

    score += liquidity.get("score", 0)
    reasons.extend(liquidity.get("reasons", []))

    return {
        "score": score,
        "reasons": reasons,
        "structure": structure,
        "volume": volume,
        "liquidity": liquidity,
    }
