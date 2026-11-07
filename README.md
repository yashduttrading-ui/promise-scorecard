# Promise Scorecard

What Indian company managements guided on earnings calls vs what they later reported, with the exact transcript page for both.

- `data/companies/<SYMBOL>.json` – hand-checked claims, outcomes and citations
- `data/companies/<SYMBOL>.sources.json` – source PDFs (company IR site), with sha256
- `scripts/fetch.py` – download the source PDFs into `raw/`
- `scripts/verify.py` – fails unless every quote is on the cited page and attributed to the right speaker
- `scripts/build.py` – renders the static site into `site/`

```bash
pip install pymupdf
cd scripts && python3 fetch.py KAYNES && python3 verify.py KAYNES && python3 build.py
```

Facts only, not investment advice.
