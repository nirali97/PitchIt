"""Case library. Numbers are computed (via quant.py) so every case is internally
consistent. Each case has a fact pool: facts with no tags are given up front; tagged
facts are revealed only when the candidate asks about that topic (progressive reveal)."""
from .quant import pct_change, break_even_units

F = lambda text, *tags: {"text": text, "tags": list(tags)}


def _case(key, title, type_, diff, client, industry, prompt, opening, exhibits, facts, context=None):
    return key, {
        "title": title, "type": type_, "difficulty": diff, "client": client, "industry": industry,
        "prompt": prompt, "opening_question": opening, "exhibits": exhibits, "fact_pool": facts,
        "context": context or "Fictional company. Treat all figures supplied during the interview as case facts.",
    }


def _profit_case(key, title, diff, client, industry, unit, n, pr, cr, pc, cc, volume_chg, driver_note):
    """Profitability case: pr/cr = prior/current revenue, pc/cc = prior/current cost (₹ crore)."""
    pp, cp = pr - pc, cr - cc
    chg = pct_change(pp, cp)
    price_chg = ((cr / pr) / (1 + volume_chg / 100) - 1) * 100
    fixed = round(pc * 0.5, 1)
    prompt = (f"{client} runs {n} {unit} in India. Over the last 12 months its operating profit has "
              f"{'fallen' if chg < 0 else 'risen'} by {abs(chg):.0f}%. The CEO wants to know why and what to do. "
              f"How would you approach this?")
    facts = [
        F(f"Revenue moved from ₹{pr} crore to ₹{cr} crore ({pct_change(pr, cr):+.1f}%)."),
        F(f"Operating costs moved from ₹{pc} crore to ₹{cc} crore ({pct_change(pc, cc):+.1f}%)."),
        F(f"The number of {unit} is unchanged at {n}."),
        F(f"Volume changed by {volume_chg:+.1f}% and average realised price by {price_chg:+.1f}%.",
          "price", "volume", "revenue", "sales", "customer", "traffic"),
        F(f"Fixed costs were unchanged at about ₹{fixed} crore; variable costs rose from ₹{round(pc - fixed, 1)} "
          f"crore to ₹{round(cc - fixed, 1)} crore.", "fixed", "variable", "cost", "expense"),
        F(driver_note, "driver", "why", "cause", "supplier", "input", "competitor", "market", "labour", "labor",
          "wage", "fuel", "hypothesis"),
    ]
    return _case(key, title, "Profitability", diff, client, industry, prompt, "How would you structure the problem?",
                 {"baseline": {"units": n, "prior_revenue_cr": pr, "current_revenue_cr": cr,
                               "prior_cost_cr": pc, "current_cost_cr": cc, "profit_change_pct": round(chg, 1)}}, facts)


def _build():
    c = dict([
        _profit_case("profitability_coffee", "The shrinking coffee chain", "Beginner", "BrewHouse", "Food & Beverage",
                     "stores", 40, 80, 80, 60, 64, 0.0, "Coffee bean and dairy input prices rose; menu prices were not changed."),
        _profit_case("profitability_bakery", "The bakery that sells less", "Beginner", "CrustCo", "Food & Beverage",
                     "outlets", 55, 120, 108, 100, 98, -12.0, "A new rival chain opened near 20 outlets and runs a loyalty scheme."),
        _profit_case("profitability_airline", "Regional airline margin squeeze", "Intermediate", "SkyHop", "Aviation",
                     "aircraft", 24, 500, 540, 450, 520, 5.0, "Aviation fuel prices rose sharply and no fuel hedge was in place."),
        _profit_case("profitability_grocer", "Growth without profit", "Intermediate", "FreshCart", "Retail",
                     "dark stores", 90, 200, 260, 190, 252, 22.0, "Delivery-partner incentives were raised to meet 10-minute delivery promises."),
        _profit_case("profitability_hospital", "Hospitals under pressure", "Intermediate", "CareLine", "Healthcare",
                     "hospitals", 12, 300, 312, 270, 285, 2.0, "Nurse and technician wages rose about 12%; bed occupancy was broadly flat."),
        _profit_case("profitability_steel", "The steelmaker's thin margin", "Advanced", "IronArc", "Manufacturing",
                     "plants", 3, 900, 810, 780, 750, -6.0, "Cheaper imported steel pushed prices down while coking-coal costs stayed high."),
    ])
    be = break_even_units(24e7, 450, 300)  # fixed ₹24 cr, price ₹450, var cost ₹300
    c.update([
        _case("breakeven_mealkit", "Meal-kit break-even", "Quant / Break-even", "Beginner", "NutriBox", "Food Tech",
              "NutriBox is a meal-kit startup deciding whether to scale. How many boxes must it sell a year to break even, and is that realistic?",
              "What would you need to know to calculate the break-even volume?",
              {"unit_economics": {"fixed_cost_cr": 24, "price_rs": 450, "variable_cost_rs": 300, "break_even_units": be}},
              [F("The business is currently loss-making and has about 200,000 customers."),
               F("Average price per box is ₹450.", "price", "revenue"),
               F("Variable cost per box (ingredients, packing, delivery) is ₹300.", "variable", "cost", "margin"),
               F("Annual fixed costs (kitchen, tech, salaries) are ₹24 crore.", "fixed", "cost"),
               F("Each customer orders about 6 boxes a year today.", "customer", "frequency", "volume", "order")]),
        _case("pricing_streaming", "Pricing a streaming subscription", "Pricing", "Intermediate", "StreamNest", "Media",
              "StreamNest, a video streaming service, is considering raising its monthly price from ₹199 to ₹249 (+25%). Should it?",
              "How would you decide whether the price increase is a good idea?",
              {"pricing": {"old_price": 199, "new_price": 249, "price_change_pct": round(pct_change(199, 249), 1), "subscribers_m": 10}},
              [F("StreamNest has 10 million paying subscribers at ₹199 per month."),
               F("The service's content cost is largely fixed.", "cost", "fixed", "margin"),
               F("A pilot raising price 25% in one city increased churn from 2% to 4% a month.", "churn", "elasticity", "test", "pilot", "demand", "customer"),
               F("The two main competitors charge ₹149 and ₹299 for comparable libraries.", "competitor", "competition", "benchmark", "market")]),
        _case("sizing_cloud_kitchens", "Sizing the cloud-kitchen market", "Market Sizing", "Beginner", "CloudChef", "Food Tech",
              "CloudChef wants to know the annual market size of online food delivery in one large Indian metro. Estimate it.",
              "How would you structure a market-size estimate?",
              {"assumptions_given": {"households_m": 3.5}},
              [F("The metro has about 3.5 million households."),
               F("About 40% of households order delivery at least monthly.", "household", "penetration", "segment", "customer"),
               F("Ordering households place about 5 orders a month on average.", "frequency", "orders", "order"),
               F("Average order value is about ₹400.", "value", "price", "basket", "ticket")]),
        _case("ma_autoparts", "Acquiring a rival supplier", "M&A", "Advanced", "Torque Motors", "Auto Components",
              "Torque Motors may acquire a smaller rival, PrecisionWorks, for ₹360 crore. Should it?",
              "What would you want to assess before recommending the deal?",
              {"deal": {"target_revenue_cr": 300, "ebitda_margin_pct": 12, "target_ebitda_cr": 36, "price_cr": 360,
                        "implied_multiple": 10.0, "annual_synergy_cr": 15}},
              [F("PrecisionWorks has revenue of ₹300 crore and a 12% EBITDA margin."),
               F("The asking price is ₹360 crore.", "price", "valuation", "multiple"),
               F("Management expects ₹15 crore of annual cost synergies from procurement and plant overlap.", "synergy", "synergies", "cost"),
               F("Two customers account for 55% of PrecisionWorks revenue.", "customer", "risk", "concentration"),
               F("Integration is expected to cost ₹40 crore one-off.", "integration", "cost", "risk")]),
        _case("ops_quickship", "Late deliveries at a logistics firm", "Operations", "Intermediate", "QuickShip", "Logistics",
              "QuickShip's on-time delivery rate has dropped from 94% to 86% in six months. Find the cause and propose a fix.",
              "How would you diagnose where the delays come from?",
              {"ops": {"on_time_before_pct": 94, "on_time_now_pct": 86}},
              [F("Order volume grew 18% in the period with no change in fleet size."),
               F("Average hub processing time rose from 3.1 to 4.4 hours.", "hub", "warehouse", "process", "sorting", "bottleneck"),
               F("Delivery-partner attrition rose from 4% to 11% a quarter.", "driver", "partner", "attrition", "labour", "labor", "staff"),
               F("Most late parcels originate from two of the five hubs.", "where", "region", "segment", "location", "hub")]),
        _case("growth_edtech", "Reigniting growth at an edtech firm", "Growth Strategy", "Intermediate", "LearnLoop", "Education",
              "LearnLoop's revenue growth has slowed from 60% to 15% year on year. The board wants a growth plan.",
              "How would you structure the path to re-accelerate growth?",
              {"growth": {"growth_before_pct": 60, "growth_now_pct": 15}},
              [F("LearnLoop sells subscription test-prep courses to school students."),
               F("New-customer acquisition cost doubled while conversion fell from 8% to 5%.", "acquisition", "cac", "marketing", "conversion", "customer"),
               F("Twelve-month renewal rate is 48%.", "retention", "renewal", "churn"),
               F("The firm has no offering for college entrance exams, a segment twice the size of its current one.", "segment", "product", "adjacent", "market", "expand")]),
        _case("market_entry_ev", "Electric vehicle charging market entry", "Market Entry", "Intermediate", "VoltWay", "Mobility",
              "VoltWay, an Indian energy company, is considering entering the public EV charging market in two metropolitan regions. The board wants a recommendation. How would you assess the opportunity?",
              "What would you want to investigate before recommending whether VoltWay should enter?",
              {"illustrative": {"target_cities": 2, "estimated_sites": 500, "investment_per_site_lakh": 18}},
              [F("The company has energy procurement experience but no charging network today."),
               F("The board has a five-year investment horizon."),
               F("The plan is 500 sites at ₹18 lakh each, a total of ₹90 crore.", "investment", "capex", "cost", "economics"),
               F("EVs are about 2% of new car sales in the two regions, growing quickly.", "demand", "market", "adoption", "size"),
               F("Two competitors already hold roughly 60% of public chargers in the regions.", "competitor", "competition", "share")]),
    ])
    return c


CASES = _build()


def public_case(case: dict, revealed_idx: list[int] | None = None) -> dict:
    """Case as shown to the candidate: only revealed facts, no answer-bearing exhibits."""
    from .interviewer import fact_texts
    out = {k: v for k, v in case.items() if k not in ("fact_pool", "exhibits")}
    out["facts"] = fact_texts(case, revealed_idx if revealed_idx is not None else initial_indices(case))
    return out


def initial_indices(case: dict) -> list[int]:
    return [i for i, f in enumerate(case["fact_pool"]) if not f["tags"]]
