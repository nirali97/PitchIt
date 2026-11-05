import re
from app.services.cases import CASES, public_case, initial_indices
from app.services.interviewer import update_reveals, fact_texts, stage_question
from app.services.quant import pct_change


def test_library_is_consistent():
    assert len(CASES) >= 13
    for k, c in CASES.items():
        assert c["prompt"] and c["opening_question"] and c["fact_pool"], k
        assert initial_indices(c), f"{k} has no opening facts"


def test_profitability_prompt_matches_numbers():
    for k, c in CASES.items():
        b = c["exhibits"].get("baseline")
        if not b:
            continue
        pct = abs(pct_change(b["prior_revenue_cr"] - b["prior_cost_cr"], b["current_revenue_cr"] - b["current_cost_cr"]))
        assert f"{pct:.0f}%" in c["prompt"], k


def test_public_case_hides_pool_and_gated_facts():
    pub = public_case(CASES["profitability_coffee"])
    assert "fact_pool" not in pub and "exhibits" not in pub
    assert not any("Fixed costs" in f for f in pub["facts"])


def test_progressive_reveal():
    c = CASES["profitability_coffee"]
    rev, new = update_reveals(c, "Let me look at revenue: price and volume.", initial_indices(c))
    assert any("Volume changed" in t for t in fact_texts(c, new))
    rev2, new2 = update_reveals(c, "price again", rev)
    assert new2 == []                       # no repeat reveals
    assert not any("Fixed costs" in t for t in fact_texts(c, rev2))


def test_stage_question_never_repeats():
    asked = []
    for _ in range(5):
        q = stage_question(["I will look at costs."], asked)
        assert q not in asked
        asked.append(q)
