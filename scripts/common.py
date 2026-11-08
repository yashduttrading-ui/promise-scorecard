import json, re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"

def norm(s):
    return re.sub(r"\s+", " ", s).strip()

def num(s):
    return float(s.replace(",", ""))

PER_CRORE = {"million": 10, "lakh": 100, "crore": 1}

def audited_value(a):
    """Recompute the reported figure from the audited lines (₹ million unless a["unit"] says otherwise). Returns (value, working)."""
    L = {k: num(v[1].replace("(", "-").replace(")", "")) for k, v in a["lines"].items()}
    raw = {k: v[1] for k, v in a["lines"].items()}
    unit = a.get("unit", "million")
    if a["measure"] == "revenue":
        v = L["rev"] / PER_CRORE[unit]
        return round(v, 1), f"₹{raw['rev']} {unit} ÷ {PER_CRORE[unit]} = ₹{v:,.2f} crore → ₹{v:,.1f} cr"
    if a["measure"] == "revenue_growth":
        v = (L["rev"] / L["rev_prev"] - 1) * 100
        return round(v, 1), f"{raw['rev']} ÷ {raw['rev_prev']} − 1 = {v:.2f}% → {v:.1f}%"
    if a["measure"] == "pat_margin":
        v = L["pat"] / L["rev"] * 100
        return round(v, 1), f"{raw['pat']} ÷ {raw['rev']} = {v:.2f}% → {v:.1f}%"
    if a["measure"] == "ebitda_margin":
        e = L["pbt"] + L["fc"] + L["da"] - L["oi"]
        v = e / L["rev"] * 100
        return round(v, 1), (f"EBITDA = {raw['pbt']} + {raw['fc']} + {raw['da']} − {raw['oi']} = {e:,.2f}; "
                             f"{e:,.2f} ÷ {raw['rev']} = {v:.2f}% → {v:.1f}%")
    raise ValueError(a["measure"])

FORMULA = {"revenue": "Revenue from operations, converted to ₹ crore (₹1 crore = ₹10 million = ₹100 lakh).",
           "revenue_growth": "Revenue from operations for the year ÷ the previous year's, minus 1.",
           "pat_margin": "Profit for the year ÷ revenue from operations.",
           "ebitda_margin": "EBITDA is not an audited line, so it is rebuilt as profit before tax (before exceptional items) "
                            "+ finance cost + depreciation − other income, then divided by revenue from operations."}

def load_company(symbol):
    c = json.loads((ROOT / "data/companies" / f"{symbol}.json").read_text())
    srcs = json.loads((ROOT / "data/companies" / f"{symbol}.sources.json").read_text())
    c["sources"] = {s.get("key") or s["date"] + ("_bizupdate" if "bizupdate" in s["file"] else ""): s for s in srcs}
    last_call = max(s["date"] for s in c["sources"].values() if s.get("kind") != "audited")
    for cl in c["claims"]:
        cl["_reported"] = last_call  # a passed deadline is only scored once a call after it has been read
        o = cl["outcome"]
        if o.get("audited"):
            o["call_value"] = o.get("value")
            o.setdefault("unit", cl["target"]["unit"])
            o["value"], o["audited"]["working"] = audited_value(o["audited"])
    return c

def is_audited(c, doc):
    return c["sources"][doc].get("kind") == "audited"

def _ocr_page(pg, cache, dpi=300):
    if cache.exists():
        return cache.read_text()
    t = pg.get_text(textpage=pg.get_textpage_ocr(dpi=dpi, full=True))
    cache.parent.mkdir(exist_ok=True)
    cache.write_text(t)
    return t

def _source(symbol, doc):
    srcs = json.loads((ROOT / "data/companies" / f"{symbol}.sources.json").read_text())
    return next((s for s in srcs if (s.get("key") or s["date"]) == doc), {})

def page_text(symbol, doc, page, dpi=None):
    """Text of one PDF page; scanned pages (no text layer) are OCR'd with Tesseract and cached in raw/ocr/."""
    import pymupdf
    with pymupdf.open(RAW / f"{symbol}_{doc}.pdf") as d:
        pg = d[page - 1]
        t = pg.get_text()
        src = _source(symbol, doc)
        if dpi or len(t.strip()) < 50 or page in src.get("ocr_pages", []):
            dpi = dpi or src.get("ocr_dpi", 300)
            t = _ocr_page(pg, RAW / "ocr" / (f"{symbol}_{doc}_p{page}" + (f"_dpi{dpi}" if dpi != 300 else "") + ".txt"), dpi)
        return norm(t)

def doc_text(symbol, doc):
    import pymupdf
    with pymupdf.open(RAW / f"{symbol}_{doc}.pdf") as d:
        return [norm(p.get_text()) for p in d]

def all_citations(c):
    for cl in c["claims"]:
        for s in cl["said"]:
            yield cl["id"], "said", s
            if s.get("cont"):
                yield cl["id"], "said (continued)", {"doc": s["doc"], **s["cont"]}
        if cl["outcome"].get("audited"):
            yield cl["id"], "audited", cl["outcome"]["audited"]
        if cl["outcome"].get("quote"):
            yield cl["id"], "outcome", cl["outcome"]
        if cl.get("management_response"):
            yield cl["id"], "response", cl["management_response"]
        if cl.get("context"):
            yield cl["id"], "context", cl["context"]
        if cl.get("reason", {}).get("quote"):
            yield cl["id"], "reason", cl["reason"]
