# Scope 3 Spend Estimator

Turns a purchase ledger into a first-pass Scope 3 footprint. Each line is a NAICS code
and a dollar amount; the estimate is spend × the EPA Supply Chain GHG Emission Factor
(v1.3, kg CO2e per 2022 USD, purchaser price, all GHGs).

```bash
python3 scope3.py examples/spend.csv            # CLI, standard library only
python3 -m unittest test_scope3                 # tests
open index.html                                 # same logic in the browser, works offline
open story.html                                 # the data story: seven angles on the factors
```

```
Total: 603.7 t CO2e on $1,210,000 matched spend (0.499 kg/USD)

Hotspots
   39.0%       235.4 t  327310  Cement for warehouse slab
   20.7%       125.0 t  484121  Long-haul trucking
   18.3%       110.2 t  331110  Structural steel
   ...
Not estimated: 3 lines, $137,000
  221112   $      75,000  Grid electricity  [electric power is not in the dataset; report it under Scope 2]
  5415     $      50,000  Misc IT services  [ambiguous: 4 codes from 0.080 to 0.089]
  999999   $      12,000  Unclassified vendor  [no factor for this code]
```

## Rules it refuses to bend

**No silent averaging.** A code shorter than six digits resolves only when every
six-digit code under it carries the same factor. Otherwise the line is reported with
the factor range, because an unweighted average of sub-industries is a number nobody
can defend.

**Unmatched spend stays visible.** The total covers matched spend only, and the
unmatched dollars are printed next to it, so coverage is never mistaken for completeness.

**Dollars must be 2022 dollars.** Factors are per 2022 USD. Spend from another year
needs `--to-2022` (2022 price index ÷ your year's index). Without it the tool says it
assumed 2022.

**Margins on by default.** Invoice amounts are purchaser prices, which include trade
and transport margins, so the with-margins factor applies. `--no-margins` switches to
producer-price factors for spend that excludes them.

## What the data says

The 1,016 NAICS codes map to only 386 USEEIO sectors, so many codes share a factor:
the resolution is sector-level, not company-level. Factors span two orders of
magnitude, from 0.029 kg/USD (insurance brokerage) to 3.924 (cement). In the example,
cement is 5% of spend and 39% of emissions; software is 35% of spend and 6%.
Electric power generation (2211xx) is absent from the dataset, so purchased
electricity has to be handled as Scope 2.

Spend-based factors are a screening tool for finding hotspots. Supplier-specific data
should replace them where the hotspots are.

## Files

`scope3.py` estimator and CLI · `test_scope3.py` tests · `page.template.html` +
`build_page.py` → `index.html` (factors inlined; rebuild after changing the data) ·
`story.page.html` + `story.shell.html` → `story.html` (the data story; d3 from cdnjs) ·
`data/` EPA factors v1.3 · `examples/spend.csv` sample ledger
