# Promise Scorecard

What Indian company managements guided on earnings calls vs what the audited results show, with the exact page for both.

- `data/companies/<SYMBOL>.json` – hand-checked claims, outcomes and citations
- `data/companies/<SYMBOL>.sources.json` – source PDFs (company IR site), with sha256
- `scripts/fetch.py` – download the source PDFs into `raw/`
- `scripts/verify.py` – fails unless every quote is on the cited page and attributed to the right speaker, and every audited number is printed on its cited filing page and agrees with what was said on the call
- `scripts/build.py` – renders the static site into `site/`

```bash
pip install pymupdf   # verify.py also needs tesseract-ocr: the FY25 audited filing is a scan
cd scripts && python3 fetch.py KAYNES && python3 verify.py KAYNES && python3 build.py
```

Facts only, not investment advice.

## Checking it by hand

Open `checks/<SYMBOL>.csv` in Excel or Google Sheets. One row per quote:

1. Click `open_pdf_at_page`. It opens the company's own PDF at `pdf_page` (the page number in your PDF viewer; `printed_page_label` is what is printed on the page itself).
2. Find `exact_quote` on that page (Ctrl+F a few words of it) and check the `speaker`. Mark `checked_quote_ok`.
3. Read `how_scored`, which spells out the comparison behind the `verdict`. Mark `checked_verdict_ok`.

Rows with `row_type` = `audited` are the reported financials. They cite the audited consolidated results table: `speaker` names the table and the year's column, `exact_quote` lists each line and number used, and `how_scored` shows the formula and arithmetic. Check that each number sits in that row and column. The FY25 filing is a scanned image, so Ctrl+F won't work in it; read the table by eye.

Reported revenue = revenue from operations (not total income), ₹ million ÷ 10 = ₹ crore. EBITDA isn't an audited line, so it is rebuilt as profit before tax (before exceptional items) + finance cost + depreciation − other income, ÷ revenue from operations. PAT margin = profit for the year ÷ revenue from operations. Working-capital days and milestones aren't in audited results and come from the call.

The same "How scored" line is shown under each promise on the site (expand "Quotes, source pages and working"). `scripts/verify.py` does step 2 automatically for every row.

### Evidence pack
`cd scripts && python3 evidence.py KAYNES` writes `checks/KAYNES_evidence.html` (not committed, ~5 MB): every quote next to an image of its PDF page with the quote highlighted, plus the verdict maths and tick boxes.

### Rules and quarterly updates
Scoring rules are in `RULES.md`. For a new quarter: `cd scripts && python3 new_quarter.py KAYNES 2026-11-14 <transcript-url>` downloads the transcript, registers it in the sources file and prints only the sentences a reviewer needs to read.

### What was left out
`cd scripts && python3 candidates.py KAYNES` writes `checks/KAYNES_forward_statements.csv`. It lists every sentence a management speaker said on the calls that contains a number and a forward-looking word, and marks the ones the scorecard uses (`used_in_claim`). Read the unused rows to check whether a material promise was missed. The site links to this file and to a CSV of the promise table.
