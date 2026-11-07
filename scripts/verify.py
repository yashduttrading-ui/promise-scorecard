"""Fail unless every quote appears verbatim (whitespace-normalised) on the cited PDF page,
and the named speaker is the last speaker label before the quote."""
import re, sys
from common import load_company, doc_text, page_text, norm, all_citations, is_audited

SPEAKER = re.compile(r"([A-Z][A-Za-z\.]+(?: [A-Z][A-Za-z\.]*){0,3}) ?:")

def check(symbol, c, cit):
    if cit["doc"] not in c["sources"]:
        return "unknown doc"
    pages = doc_text(symbol, cit["doc"])
    if not 1 <= cit["page"] <= len(pages):
        return "page out of range"
    q = norm(cit["quote"])
    i = pages[cit["page"] - 1].find(q)
    if i < 0:
        return "quote not on page"
    before = " ".join(pages[:cit["page"] - 1] + [pages[cit["page"] - 1][:i]])
    labels = [m.group(1) for m in SPEAKER.finditer(before)]
    last = labels[-1] if labels else ""
    if cit.get("speaker") and cit["speaker"].split()[-1] not in last:
        return f"speaker mismatch (transcript says {last!r})"
    return None

def check_audited(symbol, c, cl, a):
    """Each audited number must be printed on the cited page, and must match what management said on the call."""
    if not is_audited(c, a["doc"]):
        return "not an audited source"
    text = page_text(symbol, a["doc"], a["page"])
    missing = [f"{lbl} {v}" for lbl, v in a["lines"].values() if v not in text]
    if missing:
        return "not on page: " + "; ".join(missing)
    o = cl["outcome"]
    if o["call_value"] != o["value"]:
        return f"call says {o['call_value']}, audited works out to {o['value']}"
    return None

def main(symbol):
    c = load_company(symbol)
    bad = 0
    claims = {cl["id"]: cl for cl in c["claims"]}
    for cid, kind, cit in all_citations(c):
        err = check_audited(symbol, c, claims[cid], cit) if kind == "audited" else check(symbol, c, cit)
        print(("ok   " if not err else "FAIL ") + f"{cid} {kind} {cit['doc']} p{cit['page']}" + (f": {err}" if err else ""))
        bad += bool(err)
    print(f"{bad} failures")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "KAYNES")
