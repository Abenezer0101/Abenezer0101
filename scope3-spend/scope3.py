"""Spend-based Scope 3 estimator on the EPA Supply Chain GHG Emission Factors v1.3.

Each spend line is (NAICS code, USD). Emissions = spend in 2022 USD x factor, where
the factor is kg CO2e per 2022 USD at purchaser price, margins included.

A code shorter than six digits is accepted only when every six-digit code under it
shares one factor; otherwise the line is reported as ambiguous with the factor
range, never silently averaged.
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).parent / "data" / "SupplyChainGHGEmissionFactors_v1.3.0_NAICS_CO2e_USD2022.csv"

SECTORS = {
    "11": "Agriculture, Forestry, Fishing", "21": "Mining, Oil and Gas", "22": "Utilities",
    "23": "Construction", "31": "Manufacturing", "32": "Manufacturing", "33": "Manufacturing",
    "42": "Wholesale Trade", "44": "Retail Trade", "45": "Retail Trade",
    "48": "Transportation and Warehousing", "49": "Transportation and Warehousing",
    "51": "Information", "52": "Finance and Insurance", "53": "Real Estate and Leasing",
    "54": "Professional and Technical Services", "55": "Management of Companies",
    "56": "Administrative and Waste Services", "61": "Educational Services",
    "62": "Health Care and Social Assistance", "71": "Arts and Recreation",
    "72": "Accommodation and Food Services", "81": "Other Services",
}


def load_factors(path=DATA):
    """Return {six-digit code: (title, factor with margins, factor without margins)}."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return {
            r["2017 NAICS Code"]: (
                r["2017 NAICS Title"],
                float(r["Supply Chain Emission Factors with Margins"]),
                float(r["Supply Chain Emission Factors without Margins"]),
            )
            for r in csv.DictReader(f)
        }


def resolve(code, factors, margins=True):
    """Return (factor, title, None) or (None, None, reason)."""
    code = code.strip()
    if not code.isdigit() or not 2 <= len(code) <= 6:
        return None, None, "not a NAICS code"
    if code in factors:
        title, with_m, without_m = factors[code]
        return (with_m if margins else without_m), title, None
    under = [c for c in factors if c.startswith(code)]
    if not under:
        if code.startswith("2211") or "2211".startswith(code):
            return None, None, "electric power is not in the dataset; report it under Scope 2"
        return None, None, "no factor for this code"
    values = {factors[c][1 if margins else 2] for c in under}
    if len(values) == 1:
        return values.pop(), f"{SECTORS.get(code[:2], code)} ({len(under)} codes, one factor)", None
    return None, None, f"ambiguous: {len(under)} codes from {min(values):.3f} to {max(values):.3f}"


def estimate(lines, factors, to_2022=1.0, margins=True):
    """lines: iterable of (code, spend, label). Returns (rows, unmatched)."""
    rows, unmatched = [], []
    for code, spend, label in lines:
        factor, title, reason = resolve(code, factors, margins)
        if reason:
            unmatched.append((code, spend, label, reason))
            continue
        usd = spend * to_2022
        rows.append({"code": code, "label": label, "title": title, "spend": spend,
                     "factor": factor, "kg": usd * factor})
    return rows, unmatched


def read_spend(path):
    """CSV with columns naics, spend and optionally label."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        cols = {c.lower().strip(): c for c in reader.fieldnames or []}
        if "naics" not in cols or "spend" not in cols:
            sys.exit(f"{path}: needs 'naics' and 'spend' columns, got {reader.fieldnames}")
        for r in reader:
            raw = r[cols["spend"]].replace(",", "").replace("$", "").strip()
            label = r.get(cols.get("label", ""), "") or ""
            yield r[cols["naics"]], float(raw), label


def report(rows, unmatched, to_2022, out=sys.stdout):
    total = sum(r["kg"] for r in rows)
    spend = sum(r["spend"] for r in rows)
    w = out.write
    w(f"Total: {total / 1000:,.1f} t CO2e on ${spend:,.0f} matched spend")
    w(f" ({total / spend:.3f} kg/USD)\n" if spend else "\n")
    if to_2022 == 1.0:
        w("Spend treated as 2022 USD. Other years: pass --to-2022 (2022 price index / your year's).\n")

    w("\nHotspots\n")
    for r in sorted(rows, key=lambda r: -r["kg"])[:10]:
        share = r["kg"] / total if total else 0
        w(f"  {share:6.1%}  {r['kg'] / 1000:10,.1f} t  {r['code']:<6}  {r['label'] or r['title']}\n")

    by = defaultdict(float)
    for r in rows:
        by[SECTORS.get(r["code"][:2], r["code"][:2])] += r["kg"]
    w("\nBy sector\n")
    for name, kg in sorted(by.items(), key=lambda kv: -kv[1]):
        w(f"  {kg / total if total else 0:6.1%}  {kg / 1000:10,.1f} t  {name}\n")

    if unmatched:
        miss = sum(u[1] for u in unmatched)
        w(f"\nNot estimated: {len(unmatched)} lines, ${miss:,.0f}\n")
        for code, s, label, reason in unmatched:
            w(f"  {code:<8} ${s:>12,.0f}  {label}  [{reason}]\n")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("spend", help="CSV with naics, spend and optional label columns")
    p.add_argument("--to-2022", type=float, default=1.0, metavar="RATIO",
                   help="multiplier converting your spend to 2022 USD (default 1)")
    p.add_argument("--no-margins", action="store_true",
                   help="use producer-price factors (spend excludes trade and transport margins)")
    p.add_argument("--factors", default=DATA, help="factor CSV (default: bundled v1.3)")
    a = p.parse_args(argv)
    rows, unmatched = estimate(read_spend(a.spend), load_factors(a.factors), a.to_2022, not a.no_margins)
    report(rows, unmatched, a.to_2022)


if __name__ == "__main__":
    main()
