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

## Checking it by hand

Open `checks/<SYMBOL>.csv` in Excel or Google Sheets. One row per quote:

1. Click `open_pdf_at_page`. It opens the company's own PDF at `pdf_page` (the page number in your PDF viewer; `printed_page_label` is what is printed on the page itself).
2. Find `exact_quote` on that page (Ctrl+F a few words of it) and check the `speaker`. Mark `checked_quote_ok`.
3. Read `how_scored`, which spells out the comparison behind the `verdict`. Mark `checked_verdict_ok`.

The same "How scored" line is shown on every card on the site. `scripts/verify.py` does step 2 automatically for every row.
