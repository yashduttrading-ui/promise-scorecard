import json, re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"

def norm(s):
    return re.sub(r"\s+", " ", s).strip()

def num(s):
    return float(s.replace(",", ""))

def audited_value(a):
    """Recompute the reported figure from the audited lines (₹ million). Returns (value, working)."""
    L = {k: num(v[1]) for k, v in a["lines"].items()}
    raw = {k: v[1] for k, v in a["lines"].items()}
    if a["measure"] == "revenue":
        v = L["rev"] / 10
        return round(v, 1), f"₹{raw['rev']} million ÷ 10 = ₹{v:,.2f} crore → ₹{v:,.1f} cr"
    if a["measure"] == "pat_margin":
        v = L["pat"] / L["rev"] * 100
        return round(v, 1), f"{raw['pat']} ÷ {raw['rev']} = {v:.2f}% → {v:.1f}%"
    if a["measure"] == "ebitda_margin":
        e = L["pbt"] + L["fc"] + L["da"] - L["oi"]
        v = e / L["rev"] * 100
        return round(v, 1), (f"EBITDA = {raw['pbt']} + {raw['fc']} + {raw['da']} − {raw['oi']} = {e:,.2f}; "
                             f"{e:,.2f} ÷ {raw['rev']} = {v:.2f}% → {v:.1f}%")
    raise ValueError(a["measure"])

FORMULA = {"revenue": "Revenue from operations, converted from ₹ million to ₹ crore (₹1 crore = ₹10 million).",
           "pat_margin": "Profit for the year ÷ revenue from operations.",
           "ebitda_margin": "EBITDA is not an audited line, so it is rebuilt as profit before tax (before exceptional items) "
                            "+ finance cost + depreciation − other income, then divided by revenue from operations."}

def load_company(symbol):
    c = json.loads((ROOT / "data/companies" / f"{symbol}.json").read_text())
    srcs = json.loads((ROOT / "data/companies" / f"{symbol}.sources.json").read_text())
    c["sources"] = {s.get("key") or s["date"] + ("_bizupdate" if "bizupdate" in s["file"] else ""): s for s in srcs}
    for cl in c["claims"]:
        o = cl["outcome"]
        if o.get("audited"):
            o["call_value"] = o["value"]
            o["value"], o["audited"]["working"] = audited_value(o["audited"])
    return c

def is_audited(c, doc):
    return c["sources"][doc].get("kind") == "audited"

def _ocr_page(pg, cache):
    if cache.exists():
        return cache.read_text()
    t = pg.get_text(textpage=pg.get_textpage_ocr(dpi=300, full=True))
    cache.parent.mkdir(exist_ok=True)
    cache.write_text(t)
    return t

def page_text(symbol, doc, page):
    """Text of one PDF page; scanned pages (no text layer) are OCR'd with Tesseract and cached in raw/ocr/."""
    import pymupdf
    with pymupdf.open(RAW / f"{symbol}_{doc}.pdf") as d:
        pg = d[page - 1]
        t = pg.get_text()
        if len(t.strip()) < 50:
            t = _ocr_page(pg, RAW / "ocr" / f"{symbol}_{doc}_p{page}.txt")
        return norm(t)

def doc_text(symbol, doc):
    import pymupdf
    with pymupdf.open(RAW / f"{symbol}_{doc}.pdf") as d:
        return [norm(p.get_text()) for p in d]

def all_citations(c):
    for cl in c["claims"]:
        for s in cl["said"]:
            yield cl["id"], "said", s
        if cl["outcome"].get("audited"):
            yield cl["id"], "audited", cl["outcome"]["audited"]
        if cl["outcome"].get("quote"):
            yield cl["id"], "outcome", cl["outcome"]
        if cl.get("management_response"):
            yield cl["id"], "response", cl["management_response"]
        if cl.get("context"):
            yield cl["id"], "context", cl["context"]
