"""Inline the data into index.html and story.html, so both pages work from file:// without a server."""

import json
from pathlib import Path

from scope3 import SECTORS, load_factors

here = Path(__file__).parent
page = (here / "page.template.html").read_text()
page = (page.replace("/*FACTORS*/", json.dumps(load_factors(), separators=(",", ":")))
            .replace("/*SECTORS*/", json.dumps(SECTORS))
            .replace("/*EXAMPLE*/", json.dumps((here / "examples" / "spend.csv").read_text())))
(here / "index.html").write_text(page)

# story.html: the data story (story.page.html, also the published dashboard's page) with the rows inlined.
import csv
with open(here / "data" / "SupplyChainGHGEmissionFactors_v1.3.0_NAICS_CO2e_USD2022.csv", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
story = ((here / "story.shell.html").read_text()
         .replace("/*ROWS*/", json.dumps(rows, separators=(",", ":")))
         .replace("/*PAGE*/", (here / "story.page.html").read_text()))
(here / "story.html").write_text(story)
