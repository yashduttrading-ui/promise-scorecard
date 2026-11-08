# Scoring rules

The same rules apply to every company. If a case is not covered here, add the rule before scoring it.

## 1. Sources
- Only the company's own documents (earnings-call transcripts, audited and unaudited results), taken from its investor-relations page. If a document is not on that page, or the page cannot be reached, use the copy the company filed with the exchange (NSE/BSE archive URL). No data providers, no news, no broker notes.
- Register every PDF in `data/companies/<SYM>.sources.json` with its URL, sha256 and size. If a URL goes dead or the hash changes, note it; never silently swap the file.
- A results link can be a blank placeholder (Kaynes posted a logo-only page for Q2 FY27). Check page count and text before using it.

## 2. What counts as a promise
- A numeric or dated target stated by a management speaker (someone listed under MANAGEMENT on the transcript cover). Analyst questions never count, even if management says "yes".
- Four comparable groups: **Revenue**, **Margins**, **Cash and working capital**, **Milestones** (plant, product, deadline). Anything else is **company-specific**: shown on the company page, never ranked across companies.
- The scored target is the **first** time the promise was made. Later changes are recorded as `reaffirmed`, `raised` or `cut` quotes on the same card; the verdict still uses the first number.
- Growth-rate guidance is converted to rupees with the company's own audited base-year revenue, and the arithmetic is shown.
- Every sentence considered is in `checks/<SYM>_forward_statements.csv`. A reader can see what was left out.

## 3. Reading the target
- "About / around / approximately X" → low = high = X. A miss is a miss, however small; the size of the miss is shown next to the verdict.
- "X to Y" → low = X, high = Y. "At least / minimum X" or "X plus" → low = X, open-ended.
- Margin targets are in percentage points of the stated margin. "Maintain" margin means at least the prior audited year's figure.
- Fiscal year = April–March (FY26 ends 31 March 2026). "By FY26" means on or before 31 March 2026. "H2 FY26" ends 31 March 2026. "Calendar 2025" ends 31 December 2025.
- A quarter named without a year is read with the fiscal year the speaker is in unless the sentence says otherwise.

## 4. Reading the outcome
- Financial outcomes come from the **audited consolidated** results (revenue from operations, not total income). EBITDA = PBT + finance cost + depreciation − other income, over revenue from operations, unless the company's own definition is stated and used consistently.
- Where no audited line exists (working-capital days, order book), use management's stated figure and say so on the card.
- Rounding: compare the unrounded audited figure with the target; display to one decimal.
- Verdicts: **Delivered**, **Missed**, **Late** (milestone delivered after its date), **Pending** (deadline not passed, or passed but no call after it has been read yet: a September milestone stays Pending until the November call is in). A promise withdrawn before its deadline is still scored at the deadline.

## 5. Reasons
- Each miss carries what management said about it, quoted with page and speaker. Tag: `external` (outside the company's control, as management described it), `execution` (the company's own delivery), `own-choice` (a decision the company took), `not-explained` (the calls gave no reason).
- The tag summarises the quote only. If the only related quote predates or postdates the deadline, tag `not-explained` and show the quote with a caveat.

## 6. Quarterly update, in order
1. `python3 new_quarter.py SYM DATE URL` – downloads and registers the transcript, prints new guidance and sentences touching open promises.
2. Edit `<SYM>.json`: new promises as `said`; outcomes for promises now due; `reason` for new misses.
3. `verify.py` (must print 0 failures) → `candidates.py` → `build.py` → `checksheet.py` → `evidence.py`.
4. PR with the diff of the JSON only in the description, so a reviewer can check each change against the PDF.
