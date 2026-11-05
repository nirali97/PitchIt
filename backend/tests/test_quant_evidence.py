import unittest
from app.services.evidence import find_evidence, is_verbatim
from app.services.quant import pct_change, margin_pct, break_even_units, close_enough, verify_case_baseline


class EvidenceTests(unittest.TestCase):
    def test_quotes_are_verbatim(self):
        t = "I would split revenue into price and volume. Then I would check costs. Thanks."
        ev = find_evidence(t, ["revenue", "costs"])
        self.assertEqual(len(ev), 2)
        for e in ev:
            self.assertTrue(is_verbatim(e["quote"], t))

    def test_no_match_gives_no_evidence(self):
        self.assertEqual(find_evidence("Hello there friend.", ["revenue"]), [])

    def test_fabricated_quote_rejected(self):
        self.assertFalse(is_verbatim("I never said this", "something else"))


class QuantTests(unittest.TestCase):
    def test_coffee_case_ground_truth(self):
        b = verify_case_baseline({"prior_revenue_cr": 80, "current_revenue_cr": 80, "prior_cost_cr": 60, "current_cost_cr": 64})
        self.assertEqual(b["prior_profit_cr"], 20)
        self.assertEqual(b["current_profit_cr"], 16)
        self.assertAlmostEqual(b["profit_change_pct"], -20.0)   # matches case prompt (-20%)
        self.assertAlmostEqual(b["cost_change_pct"], 6.6667, places=3)

    def test_break_even(self):
        self.assertEqual(break_even_units(1000, 20, 10), 100)
        with self.assertRaises(ValueError): break_even_units(1000, 10, 10)

    def test_zero_guards(self):
        with self.assertRaises(ValueError): pct_change(0, 5)
        with self.assertRaises(ValueError): margin_pct(0, 5)

    def test_tolerance(self):
        self.assertTrue(close_enough(6.7, 6.6667))
        self.assertFalse(close_enough(8.0, 6.6667))


if __name__ == "__main__":
    unittest.main()
