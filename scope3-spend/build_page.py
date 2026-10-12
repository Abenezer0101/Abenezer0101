"""Inline the factor CSV and the example spend into index.html, so the page works offline from file://."""

import json
from pathlib import Path

from scope3 import SECTORS, load_factors

here = Path(__file__).parent
page = (here / "page.template.html").read_text()
page = (page.replace("/*FACTORS*/", json.dumps(load_factors(), separators=(",", ":")))
            .replace("/*SECTORS*/", json.dumps(SECTORS))
            .replace("/*EXAMPLE*/", json.dumps((here / "examples" / "spend.csv").read_text())))
(here / "index.html").write_text(page)
