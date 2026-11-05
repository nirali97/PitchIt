"""Deterministic arithmetic for the Quant Lab / numerical verification.
No LLM involved; pure functions with explicit units and error handling."""


def pct_change(old: float, new: float) -> float:
    if old == 0:
        raise ValueError("pct_change: base value is zero")
    return (new - old) / abs(old) * 100.0


def margin_pct(revenue: float, cost: float) -> float:
    if revenue == 0:
        raise ValueError("margin_pct: revenue is zero")
    return (revenue - cost) / revenue * 100.0


def break_even_units(fixed_cost: float, price: float, variable_cost: float) -> float:
    cm = price - variable_cost
    if cm <= 0:
        raise ValueError("break_even_units: contribution margin must be positive")
    return fixed_cost / cm


def close_enough(candidate: float, expected: float, rel_tol: float = 0.02) -> bool:
    """Accept reasonable rounding (default 2%) so valid estimates aren't penalised."""
    if expected == 0:
        return abs(candidate) <= rel_tol
    return abs(candidate - expected) / abs(expected) <= rel_tol


def verify_case_baseline(exhibit: dict) -> dict:
    """Ground-truth figures for a case exhibit (e.g. profitability_coffee)."""
    pr, cr = exhibit["prior_revenue_cr"], exhibit["current_revenue_cr"]
    pc, cc = exhibit["prior_cost_cr"], exhibit["current_cost_cr"]
    prior_profit, current_profit = pr - pc, cr - cc
    return {
        "prior_profit_cr": prior_profit,
        "current_profit_cr": current_profit,
        "profit_change_pct": pct_change(prior_profit, current_profit),
        "cost_change_pct": pct_change(pc, cc),
        "current_margin_pct": margin_pct(cr, cc),
    }
