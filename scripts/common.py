import json, re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"

def norm(s):
    return re.sub(r"\s+", " ", s).strip()

def load_company(symbol):
    c = json.loads((ROOT / "data/companies" / f"{symbol}.json").read_text())
    srcs = json.loads((ROOT / "data/companies" / f"{symbol}.sources.json").read_text())
    c["sources"] = {s["date"] + ("_bizupdate" if "bizupdate" in s["file"] else ""): s for s in srcs}
    return c

def page_text(symbol, doc, page):
    import pymupdf
    pdf = RAW / f"{symbol}_{doc}.pdf"
    with pymupdf.open(pdf) as d:
        return norm(d[page - 1].get_text())

def doc_text(symbol, doc):
    import pymupdf
    with pymupdf.open(RAW / f"{symbol}_{doc}.pdf") as d:
        return [norm(p.get_text()) for p in d]

def all_citations(c):
    for cl in c["claims"]:
        for s in cl["said"]:
            yield cl["id"], "said", s
        if cl["outcome"].get("quote"):
            yield cl["id"], "outcome", cl["outcome"]
        if cl.get("management_response"):
            yield cl["id"], "response", cl["management_response"]
