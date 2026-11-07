"""Write checks/<SYMBOL>_evidence.html: every quote next to an image of its PDF page, quote highlighted."""
import base64, html, sys
import pymupdf
from common import ROOT, RAW, load_company, all_citations, norm, FORMULA
from build import verdict, rule_text, target_text, fmt, date_label

E = html.escape

def highlight_page(symbol, cit):
    with pymupdf.open(RAW / f"{symbol}_{cit['doc']}.pdf") as d:
        pg = d[cit["page"] - 1]
        hits = []
        if "lines" in cit:
            tp = pg.get_textpage_ocr(dpi=300, full=True) if len(pg.get_text().strip()) < 50 else None
            for lbl, v in cit["lines"].values():
                hits += pg.search_for(v, textpage=tp)
        else:
            words = norm(cit["quote"]).split()
            for i in range(0, len(words), 5):
                chunk = " ".join(words[i:i + 6])
                hits += pg.search_for(chunk)
        for r in hits:
            a = pg.add_highlight_annot(r); a.set_colors(stroke=(1, 0.85, 0.2)); a.update()
        png = pg.get_pixmap(matrix=pymupdf.Matrix(1.3, 1.3)).tobytes("jpeg", jpg_quality=65)
        return base64.b64encode(png).decode(), bool(hits)

def main(symbol):
    c = load_company(symbol)
    claims = {cl["id"]: cl for cl in c["claims"]}
    rows, n = [], 0
    for cid, kind, cit in all_citations(c):
        n += 1
        cl = claims[cid]; o = cl["outcome"]
        img, found = highlight_page(symbol, cit)
        url = c["sources"][cit["doc"]]["url"] + f"#page={cit['page']}"
        label = {"said": cit.get("role", "said"), "outcome": "reported", "response": "management response", "context": "context", "audited": "audited result"}[kind]
        reported = fmt(o["value"], o["unit"]) if "value" in o else o.get("status", "")
        if kind == "audited":
            src = f'{c["sources"][cit["doc"]]["label"]} ({c["sources"][cit["doc"]]["title"]})'
            who = f'<b>Table:</b> {E(cit["table"])}<br><b>Column:</b> {E(cit["column"])}'
            body = "<br>".join(f"{E(lbl)} = <b>{E(v)}</b>" for lbl, v in cit["lines"].values())
            maths = f'<br><b>Working:</b> {E(FORMULA[cit["measure"]])} {E(cit["working"])}'
            ask = "Each number in the right row and column of the table?"
        else:
            src = f"concall {date_label(cit['doc'])}"
            who = f"<b>Speaker claimed:</b> {E(cit.get('speaker','—'))}"
            body, maths, ask = f"“{E(cit['quote'])}”", "", "Quote on page and right speaker?"
        rows.append(f"""<section><div class=meta><div class=n>#{n}</div>
<h3>{E(cl['topic'])} <span>{E(cl['period'])}</span></h3>
<p><b>Row type:</b> {E(label)}<br><b>Source:</b> {E(src)}, PDF page {cit['page']} · <a href="{E(url)}" target=_blank>open original ↗</a><br>
{who}</p>
<blockquote>{body}</blockquote>
<p><b>Target:</b> {E(target_text(cl['target']))} · <b>Reported:</b> {E(str(reported))} · <b>Verdict:</b> {verdict(cl, c['checked_on'])[1]}<br>
<b>How scored:</b> {E(rule_text(cl, c['checked_on']))}{maths}</p>
{'' if found else '<p class=warn>Highlight not found automatically, read the page.</p>'}
<p class=tick>{ask} ☐ Y ☐ N &nbsp; Verdict right? ☐ Y ☐ N</p></div>
<img loading=lazy src="data:image/jpeg;base64,{img}" alt="PDF page {cit['page']}"></section>""")
    doc = f"""<!doctype html><meta charset=utf-8><title>{E(c['name'])}: evidence pack</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;margin:0;background:#f4f5f7;color:#111}}header{{padding:24px 32px;background:#fff;border-bottom:1px solid #ddd}}
section{{display:grid;grid-template-columns:minmax(300px,1fr) minmax(420px,1.3fr);gap:24px;background:#fff;margin:16px 32px;padding:20px;border-radius:10px;border:1px solid #e3e5e8}}
img{{width:100%;border:1px solid #ccc}}.meta{{position:sticky;top:12px;align-self:start}}h3{{margin:0 0 8px}}h3 span{{color:#777;font-weight:500}}.n{{color:#999;font-size:13px}}
blockquote{{margin:12px 0;padding:10px 14px;background:#fff7d6;border-left:4px solid #f2c200}}.warn{{color:#b00}}.tick{{color:#555;font-size:14px}}
@media(max-width:900px){{section{{grid-template-columns:1fr;margin:12px}}.meta{{position:static}}}}</style>
<header><h1>{E(c['name'])}: evidence pack</h1><p>{n} citations. Each one is shown next to the actual PDF page from the company's investor site, with the quote (or, for audited rows, each number used) highlighted in yellow.
For each row: (1) read the yellow text and check it matches the quote; (2) check the speaker name above it (if the speaker started on the previous page, use “open original” and scroll up one page);
(3) check the verdict maths in “How scored”. For audited rows, check each highlighted number sits in the named row and in the named year's column. Page images are rendered from PDFs downloaded from <a href="{E(c['ir_page'])}">{E(c['ir_page'])}</a>; their fingerprints are in KAYNES.sources.json.</p></header>
{''.join(rows)}"""
    out = ROOT / "checks" / f"{symbol}_evidence.html"
    out.write_text(doc)
    print("wrote", out, f"{out.stat().st_size/1e6:.1f} MB")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "KAYNES")
