"""Render data/companies/*.json into a static site in site/."""
import datetime as dt, html, json, sys
from common import ROOT, load_company

E = html.escape
OUT = ROOT / "site"

def fmt(v, unit):
    if unit == "%": return f"{v:g}%"
    if unit == "days": return f"{v:g} days"
    return f"₹{v:,.0f} cr" if v >= 100 else f"₹{v:g} cr"

def target_text(t):
    u = t.get("unit", "")
    return {"range": lambda: f"{fmt(t['low'], u)}–{fmt(t['high'], u)}",
            "min": lambda: f"{fmt(t['low'], u)}+",
            "max": lambda: f"≤ {fmt(t['high'], u)}",
            "milestone": lambda: t.get("label", "Milestone")}[t["kind"]]()

def verdict(cl, today):
    t, o = cl["target"], cl["outcome"]
    if o.get("status") == "pending":
        return ("pending", "Pending") if cl["deadline"] > today else ("missed", "Missed")
    if o.get("status") == "late": return "late", "Late"
    if o.get("status") == "met": return "met", "Delivered"
    v = o["value"]
    ok = v <= t["high"] if t["kind"] == "max" else v >= t["low"]
    return ("met", "Delivered") if ok else ("missed", "Missed")

def rule_text(cl, today):
    t, o = cl["target"], cl["outcome"]
    vk, vl = verdict(cl, today)
    if o.get("status") == "pending":
        return f"Deadline {date_label(cl['deadline'])} is after {date_label(today)}, so not scored yet."
    if t["kind"] == "milestone":
        if o.get("done"):
            return (f"Promised by {date_label(cl['deadline'])}. First reported done in the "
                    f"{date_label(o['first_seen'])} call, which is after the deadline → {vl}.")
        return (f"Promised by {date_label(cl['deadline'])}. Not done by then; in the latest update "
                f"({date_label(o['first_seen'])} call) it is still in the future → {vl}.")
    u, v = t.get("unit", ""), o["value"]
    if t["kind"] == "max":
        test, ok = f"{fmt(v, u)} ≤ {fmt(t['high'], u)}", v <= t["high"]
    else:
        test, ok = f"{fmt(v, u)} ≥ {fmt(t['low'], u)} (first target)", v >= t["low"]
    conv = " ₹1 crore = ₹10 million." if u == "₹ cr" and "million" in o["quote"] else ""
    return f"Is reported {test}? {'Yes' if ok else 'No'} → {vl}.{conv}"

def gap(cl):
    t, o = cl["target"], cl["outcome"]
    if "value" not in o or t["kind"] == "milestone": return ""
    ref = t["high"] if t["kind"] == "max" else t["low"]
    d = o["value"] - ref
    if t.get("unit") == "%": return f"{d:+.1f} pts vs target"
    return f"{d / ref * 100:+.0f}% vs target"

def date_label(d):
    return dt.date.fromisoformat(d[:10]).strftime("%-d %b %Y")

def cite(c, cit):
    src = c["sources"][cit["doc"]]
    return (f'<a class="cite" href="{E(src["url"])}#page={cit["page"]}" target="_blank" rel="noopener">'
            f'Concall {date_label(cit["doc"])} · p.{cit["page"]} ↗</a>')

ROLE = {"first": "Guided", "reaffirmed": "Reaffirmed", "cut": "Cut", "moved": "Moved"}

def quote_block(c, cit, label):
    who = f' — {E(cit["speaker"])}' if cit.get("speaker") else ""
    return (f'<div class="q"><div class="qhead"><span class="tag t-{E(label.lower())}">{E(label)}</span>{cite(c, cit)}</div>'
            f'<blockquote>“{E(cit["quote"])}”<span class="who">{who}</span></blockquote></div>')

def claim_card(c, cl, today):
    vk, vl = verdict(cl, today)
    o = cl["outcome"]
    said = "".join(quote_block(c, s, ROLE[s["role"]]) for s in cl["said"])
    if o.get("quote"):
        val = f'<b>{fmt(o["value"], o["unit"])}</b> <span class="gap">{gap(cl)}</span>' if "value" in o else ""
        result = f'<div class="result"><div class="rhead">{"What happened" if o.get("done", True) else "Where it stands"} {val}</div>{quote_block(c, o, "Reported" if o.get("done", True) else "Latest update")}</div>'
    else:
        result = f'<div class="result pend">Deadline {date_label(cl["deadline"])}. Nothing to score yet.</div>'
    resp = quote_block(c, cl["management_response"], "Management on it") if cl.get("management_response") else ""
    resp += quote_block(c, cl["context"], "Context") if cl.get("context") else ""
    note = f'<p class="rule"><b>How scored:</b> {E(rule_text(cl, today))}</p>'
    note += f'<p class="note">{E(cl["note"])}</p>' if cl.get("note") else ""
    return (f'<article class="card" id="{E(cl["id"])}" data-v="{vk}"><header><div><h3>{E(cl["topic"])} <span class="per">{E(cl["period"])}</span></h3>'
            f'<div class="tgt">Target: {E(target_text(cl["target"]))}</div></div><span class="pill v-{vk}">{vl}</span></header>'
            f'{said}{result}{resp}{note}</article>')

def revenue_chart(c):
    rows = []
    for cl in c["claims"]:
        if cl["topic"] != "Revenue" or "value" not in cl["outcome"]: continue
        first = cl["target"]["low"]
        cut = next((s["value"] for s in cl["said"] if s["role"] == "cut"), None)
        rows.append((cl["period"], first, cut, cl["outcome"]["value"]))
    if not rows: return ""
    W, H, pad, top = 640, 300, 56, 24
    mx = max(max(r[1], r[3]) for r in rows) * 1.12
    y = lambda v: top + (H - top - 40) * (1 - v / mx)
    gw = (W - pad - 10) / len(rows); bw = gw / 4.6
    parts = []
    for tick in range(0, int(mx), 1000):
        parts.append(f'<line x1="{pad}" x2="{W-10}" y1="{y(tick):.1f}" y2="{y(tick):.1f}" class="grid"/>'
                     f'<text x="{pad-8}" y="{y(tick)+4:.1f}" class="ax" text-anchor="end">{tick:,}</text>')
    for i, (p, first, cut, act) in enumerate(rows):
        x0 = pad + i * gw + gw * 0.14
        for j, (v, cls) in enumerate([(first, "b-guide"), (cut, "b-cut"), (act, "b-act")]):
            if v is None: continue
            x = x0 + j * (bw + 6)
            parts.append(f'<rect x="{x:.1f}" y="{y(v):.1f}" width="{bw:.1f}" height="{y(0)-y(v):.1f}" rx="4" class="{cls}"/>'
                         f'<text x="{x+bw/2:.1f}" y="{y(v)-6:.1f}" class="val" text-anchor="middle">{v:,.0f}</text>')
        parts.append(f'<text x="{x0 + 1.5*bw + 6:.1f}" y="{H-14}" class="ax" text-anchor="middle">{p}</text>')
    parts.append(f'<text x="14" y="{(H)/2:.0f}" class="ax" transform="rotate(-90 14 {H/2:.0f})" text-anchor="middle">Revenue, ₹ crore</text>')
    legend = ('<div class="legend"><span><i class="b-guide"></i>First guidance</span><span><i class="b-cut"></i>Later cut to</span>'
              '<span><i class="b-act"></i>Reported</span></div>')
    return (f'<section class="panel"><h2>Revenue: guided vs delivered</h2><svg viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="Revenue guidance versus reported revenue">{"".join(parts)}</svg>{legend}'
            f'<p class="src">Source: company concall transcripts, cited in the cards below. FY = April–March.</p></section>')

def is_open(cl, today):
    o = cl["outcome"]
    return (o.get("status") == "pending" and cl["deadline"] > today) or o.get("done") is False

def watch_list(c, today):
    items = sorted((cl for cl in c["claims"] if is_open(cl, today)),
                   key=lambda cl: (cl["outcome"].get("new_deadline", cl["deadline"]), cl["id"]))
    if not items: return ""
    rows = ""
    for cl in items:
        o, s = cl["outcome"], cl["said"][0]
        due = o.get("new_deadline", cl["deadline"])
        slipped = f' (originally {date_label(cl["deadline"])})' if "new_deadline" in o else ""
        rows += (f'<li><a href="#{E(cl["id"])}"><b>{E(cl["topic"])}</b></a> <span class="per">{E(cl["period"])}</span>'
                 f'<div class="tgt">Target: {E(target_text(cl["target"]))} · Due {date_label(due)}{E(slipped)} · '
                 f'said {date_label(s["doc"])}, {cite(c, s)}</div></li>')
    nr = c.get("next_results")
    sub = (f'Next checkpoint: <b>{E(nr["label"])}</b>, due by {date_label(nr["due"])}. ' if nr else "")
    return (f'<section class="panel watch"><h2>What to watch next</h2><p class="src">{sub}'
            f'These promises are still open, soonest first. Click one to see the full quote.</p><ul>{rows}</ul></section>')

CSS = (ROOT / "scripts/style.css").read_text()

def page(title, body, desc):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><main>{body}</main>
<footer>Built by <a href="https://app.avanisai.com">Avanis</a>. Facts only: what management said on the record and what was later reported. Not investment advice.</footer>
<script>document.querySelectorAll('.filters button').forEach(b=>b.onclick=()=>{{document.querySelectorAll('.filters button').forEach(x=>x.classList.toggle('on',x===b));
document.querySelectorAll('.card').forEach(c=>c.hidden=b.dataset.f!=='all'&&c.dataset.v!==b.dataset.f)}});
document.querySelectorAll('.watch li>a').forEach(a=>a.addEventListener('click',()=>document.querySelector('.filters button[data-f=all]').click()))</script></body></html>"""

def company_page(c):
    today = c["checked_on"]
    vs = [verdict(cl, today)[0] for cl in c["claims"]]
    n = {k: vs.count(k) for k in ("met", "missed", "late", "pending")}
    scored = n["met"] + n["missed"] + n["late"]
    stats = "".join(f'<div class="stat s-{k}"><b>{n[k]}</b><span>{l}</span></div>' for k, l in
                    [("met", "Delivered"), ("missed", "Missed"), ("late", "Late"), ("pending", "Pending")])
    filters = "".join(f'<button data-f="{k}"{" class=on" if k=="all" else ""}>{l}</button>' for k, l in
                      [("all", "All"), ("met", "Delivered"), ("missed", "Missed"), ("late", "Late"), ("pending", "Pending")])
    cards = "".join(claim_card(c, cl, today) for cl in c["claims"])
    first = min(c["sources"]); last = max(c["sources"])
    body = f"""<nav><a href="index.html">← All companies</a></nav>
<section class="hero"><div class="eyebrow">{E(c["exchange"])}: {E(c["symbol"])}</div><h1>{E(c["name"])}</h1>
<p class="lede">Management kept <b>{n["met"]} of {scored}</b> promises that are due so far. Every line links to the exact page of the company's own concall transcript.</p>
<div class="stats">{stats}</div></section>
{watch_list(c, today)}
{revenue_chart(c)}
<div class="filters">{filters}</div>{cards}
<section class="panel method"><h2>How this is built</h2><ul>
<li><b>Sources:</b> {len(c["sources"])} earnings-call transcripts from {date_label(first)} to {date_label(last)}, downloaded from <a href="{E(c["ir_page"])}">the company's investor page</a>. No third-party data.</li>
<li><b>What counts as a promise:</b> a specific, checkable number or milestone said by management (not by analysts) with a time frame.</li>
<li><b>Verdict:</b> scored against the <i>first</i> guidance given. Later cuts are shown, not hidden. Delivered = met or beat the target. Late = milestone happened after the stated date, or not yet.</li>
<li><b>Checked by script:</b> every quote is tested word-for-word against the cited PDF page, and the speaker is checked against the transcript.</li>
<li>Data as of {date_label(today)}. Spotted an error? Open an issue on GitHub.</li></ul></section>"""
    return page(f"{c['name']}: promises vs delivery | Avanis Promise Scorecard", body,
                f"{c['name']} management kept {n['met']} of {scored} promises. Every claim cited to the page.")

def index_page(cos):
    rows = ""
    for c in cos:
        vs = [verdict(cl, c["checked_on"])[0] for cl in c["claims"]]
        scored = sum(v != "pending" for v in vs)
        rows += (f'<a class="co" href="{c["symbol"].lower()}.html"><div><b>{E(c["name"])}</b><span>{E(c["exchange"])}: {E(c["symbol"])}</span></div>'
                 f'<div class="score">{vs.count("met")}/{scored} kept</div></a>')
    body = f"""<section class="hero"><div class="eyebrow">Avanis Promise Scorecard</div><h1>Did management do what they said?</h1>
<p class="lede">Free scorecards for Indian listed companies. What management guided on earnings calls, what they actually reported, and the exact page for both. No login, no API key.</p></section>
<section class="list">{rows}</section>"""
    return page("Avanis Promise Scorecard", body, "What Indian managements guided vs what they delivered, cited to the page.")

def main(symbols):
    OUT.mkdir(exist_ok=True)
    cos = [load_company(s) for s in symbols]
    for c in cos:
        (OUT / f"{c['symbol'].lower()}.html").write_text(company_page(c))
    (OUT / "index.html").write_text(index_page(cos))
    print("built", [c["symbol"] for c in cos])

if __name__ == "__main__":
    main(sys.argv[1:] or [p.stem for p in (ROOT / "data/companies").glob("*.json") if "." not in p.stem])
