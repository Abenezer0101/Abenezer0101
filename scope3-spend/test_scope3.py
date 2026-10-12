import io
import unittest

from scope3 import estimate, load_factors, report, resolve

F = load_factors()


class Scope3Test(unittest.TestCase):
    def test_dataset_shape(self):
        self.assertEqual(len(F), 1016)
        for title, with_m, without_m in F.values():
            self.assertGreaterEqual(with_m, without_m)

    def test_exact_code(self):
        self.assertEqual(resolve("327310", F), (3.924, "Cement Manufacturing", None))
        self.assertEqual(resolve("327310", F, margins=False)[0], F["327310"][2])

    def test_prefix_with_one_factor_resolves(self):
        factor, title, reason = resolve("52421", F)
        self.assertIsNone(reason)
        self.assertEqual(factor, F["524210"][1])

    def test_prefix_with_mixed_factors_is_refused(self):
        factor, _, reason = resolve("5415", F)
        self.assertIsNone(factor)
        self.assertTrue(reason.startswith("ambiguous: 4 codes"))

    def test_bad_and_missing_codes(self):
        self.assertEqual(resolve("abc", F)[2], "not a NAICS code")
        self.assertEqual(resolve("1234567", F)[2], "not a NAICS code")
        self.assertEqual(resolve("999999", F)[2], "no factor for this code")
        self.assertIn("Scope 2", resolve("221112", F)[2])
        self.assertTrue(resolve("22", F)[2].startswith("ambiguous"))

    def test_estimate_math_and_deflator(self):
        rows, unmatched = estimate([("327310", 1000, "x"), ("999999", 5, "y")], F, to_2022=0.9)
        self.assertAlmostEqual(rows[0]["kg"], 1000 * 0.9 * 3.924)
        self.assertEqual(len(unmatched), 1)

    def test_report_handles_empty(self):
        out = io.StringIO()
        report([], [("999999", 5.0, "y", "no factor")], 1.0, out)
        self.assertIn("Not estimated: 1 lines", out.getvalue())


if __name__ == "__main__":
    unittest.main()
