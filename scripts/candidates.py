"""List every forward-looking management sentence with a number, from every transcript, and mark which ones
the scorecard uses. Lets a reader check what was left out. Writes checks/<SYMBOL>_forward_statements.csv."""
import csv, re, sys
from common import ROOT, load_company, doc_text, norm, is_audited, all_citations
from verify import SPEAKER

FORWARD = re.compile(r"\b(will|expect\w*|guid\w*|target\w*|aim\w*|plan\w*|going to|outlook|next year|by FY|"
                     r"by the end of|anticipat\w*|visibility)\b", re.I)

def management(pages):
    """Surnames listed under MANAGEMENT: on the cover page. None if the document has no participant list."""
    m = re.search(r"MANAGEMENT ?:(.*?)MODERATOR", " ".join(pages[:2]), re.S)
    return m and set(re.findall(r"[A-Z]{3,}", m.group(1)))

HEADER = re.compile(r"Page \d+ of \d+|“?Kaynes Technology India Limited[^”.]{0,80}?(?:Call”\s*)?[A-Z][a-z]+ \d{1,2}, ?\d{4}")

def turns(pages):
    """Yield (page, speaker, text) for each speaker turn, carrying the speaker across page breaks."""
    who = ""
    for i, p in enumerate(pages, 1):
        pos = 0
        for m in SPEAKER.finditer(p):
            yield i, who, p[pos:m.start()]
            who, pos = m.group(1), m.end()
        yield i, who, p[pos:]

def main(symbol):
    c = load_company(symbol)
    used = [(cid, kind, norm(cit["quote"])) for cid, kind, cit in all_citations(c) if kind != "audited"]
    rows, matched = [], set()
    for key, src in sorted(c["sources"].items()):
        if is_audited(c, key): continue
        pages = [HEADER.sub(" ", p) for p in doc_text(symbol, key)]
        mgmt = management(pages)
        for page, who, text in turns(pages):
            surname = who.split()[-1].upper() if who else ""
            if mgmt is not None and surname not in mgmt: continue
            for s in re.split(r"(?<=[.?!])\s+", text):
                hits = [(cid, kind) for cid, kind, q in used if q in s or (len(s) > 30 and s in q) or q[:60] in s]
                ids = sorted({cid for cid, kind in hits if kind == "said"})
                other = sorted({f"{cid} ({kind})" for cid, kind in hits if kind != "said"})
                if not hits and (len(s.split()) < 6 or not re.search(r"\d", s) or not FORWARD.search(s)): continue
                matched.update(i for i in ids)
                rows.append([src["date"], page, who if mgmt is not None else "Company document", "; ".join(ids), "; ".join(other), s,
                             f'{src["url"]}#page={page}'])
    out = ROOT / "checks" / f"{symbol}_forward_statements.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["call_date", "page", "speaker", "used_in_claim", "cited_as_outcome_or_context", "sentence", "open_pdf_at_page"])
        w.writerows(rows)
    print(f"{len(rows)} sentences, {sum(bool(r[3]) for r in rows)} used as promises, {sum(bool(r[4]) and not r[3] for r in rows)} as other citations; claims matched {len(matched)}/{len(c['claims'])}")
    print("unmatched claims:", [cl["id"] for cl in c["claims"] if cl["id"] not in matched])

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "KAYNES")
