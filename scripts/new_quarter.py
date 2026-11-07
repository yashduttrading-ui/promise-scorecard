"""Prepare a quarterly update. Downloads one new transcript, registers it in <SYMBOL>.sources.json, and prints only
what a reviewer needs to read: every forward-looking management sentence with a number (new guidance), and every
management sentence that mentions a promise still open on the scorecard (outcomes). Judgment stays with the reviewer.

usage: python3 new_quarter.py SYMBOL YYYY-MM-DD URL ["Title"]
"""
import hashlib, json, re, subprocess, sys
from common import ROOT, RAW, load_company, doc_text
from candidates import FORWARD, HEADER, management, turns

STOP = set("the and for from with that this will revenue growth margin days business first production target fy by of to in".split())

def register(symbol, date, url, title):
    path = ROOT / "data/companies" / f"{symbol}.sources.json"
    srcs = json.loads(path.read_text())
    out = RAW / f"{symbol}_{date}.pdf"
    RAW.mkdir(exist_ok=True)
    if not out.exists():
        subprocess.run(["curl", "-sfL", "-A", "Mozilla/5.0", "-o", str(out), url], check=True)
    data = out.read_bytes()
    if not any(s["date"] == date and "key" not in s for s in srcs):
        srcs.append({"file": out.name, "date": date, "title": title, "url": url,
                     "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        path.write_text(json.dumps(srcs, indent=1, ensure_ascii=False) + "\n")
    pages = doc_text(symbol, date)
    if sum(len(p) for p in pages) < 500:
        sys.exit(f"{out.name}: {len(pages)} page(s) with almost no text. Placeholder or scan? Check it by eye before using.")
    return pages

def main(symbol, date, url, title):
    pages = register(symbol, date, url, title)
    c = load_company(symbol)
    open_claims = [cl for cl in c["claims"] if cl["outcome"].get("status") in ("pending", "late")]
    words = {cl["id"]: {w for w in re.findall(r"[a-z]{4,}", cl["topic"].lower()) if w not in STOP} for cl in open_claims}
    pages = [HEADER.sub(" ", p) for p in pages]
    mgmt = management(pages)
    guidance, outcomes = [], []
    for page, who, text in turns(pages):
        name = re.findall(r"[A-Z]{3,}", who.split(". ")[-1].upper())
        if mgmt is not None and not (name and all(n in mgmt for n in name)): continue
        for s in re.split(r"(?<=[.?!])\s+", text):
            if len(s.split()) < 6: continue
            low = s.lower()
            hits = [cid for cid, ws in words.items() if ws and ws & set(re.findall(r"[a-z]{4,}", low))]
            if re.search(r"\d", s) and FORWARD.search(s): guidance.append((page, who, s))
            if hits: outcomes.append((page, who, s, hits))
    print(f"\n== {symbol} {date}: {len(pages)} pages, {len(guidance)} forward-looking sentences with a number ==")
    for p, w, s in guidance: print(f"  p{p} {w}: {s}")
    print(f"\n== Sentences touching the {len(open_claims)} open promises ({len(outcomes)}) ==")
    for p, w, s, h in outcomes: print(f"  p{p} {w} [{', '.join(h)}]: {s}")
    print("\nNext: add new promises to the JSON as `said`, record outcomes for due ones, then run "
          "verify.py, candidates.py, build.py, checksheet.py, evidence.py in that order. See RULES.md.")

if __name__ == "__main__":
    if len(sys.argv) < 4: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else f"Earnings call transcript {sys.argv[2]}")
