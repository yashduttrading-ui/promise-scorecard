"""Render data/companies/*.json into a static site in site/."""
import csv, datetime as dt, html, io, json, shutil, sys
from common import ROOT, load_company, is_audited, FORMULA

E = html.escape
OUT = ROOT / "site"
SITE_URL = "https://yashduttrading-ui.github.io/promise-scorecard/"
EMAIL = "yash@avanisai.com"

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
    src = "audited" if o.get("audited") else "reported"
    conv = " ₹1 crore = ₹10 million." if u == "₹ cr" and (o.get("audited") or "million" in o["quote"]) else ""
    return f"Is {src} {test}? {'Yes' if ok else 'No'} → {vl}.{conv}"

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
    name = src["label"] if is_audited(c, cit["doc"]) else f'Concall {date_label(cit["doc"])}'
    return (f'<a class="cite" href="{E(src["url"])}#page={cit["page"]}" target="_blank" rel="noopener">'
            f'{E(name)} · p.{cit["page"]} ↗</a>')

def audited_block(c, o):
    a = o["audited"]
    rows = "".join(f'<tr><td>{E(lbl)}</td><td>{E(v)}</td></tr>' for lbl, v in a["lines"].values())
    said = (f'Matches the {fmt(o["call_value"], o["unit"])} management stated on the call.' if o["call_value"] == o["value"]
            else f'Management said {fmt(o["call_value"], o["unit"])} on the call; the audited figure is used.')
    return (f'<div class="q aud"><div class="qhead"><span class="tag t-audited">Audited</span>{cite(c, a)}</div>'
            f'<div class="audcol">{E(a["table"])}, column “{E(a["column"])}”</div>'
            f'<table>{rows}</table><p class="calc">{E(FORMULA[a["measure"]])}<br><b>{E(a["working"])}</b>. {E(said)}</p></div>')

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
        aud = audited_block(c, o) if o.get("audited") else ""
        label = "Said on call" if aud else "Reported" if o.get("done", True) else "Latest update"
        result = f'<div class="result"><div class="rhead">{"What happened" if o.get("done", True) else "Where it stands"} {val}</div>{aud}{quote_block(c, o, label)}</div>'
    else:
        result = f'<div class="result pend">Deadline {date_label(cl["deadline"])}. Nothing to score yet.</div>'
    resp = quote_block(c, cl["management_response"], "Management on it") if cl.get("management_response") else ""
    resp += quote_block(c, cl["context"], "Context") if cl.get("context") else ""
    note = f'<p class="rule"><b>How scored:</b> {E(rule_text(cl, today))}</p>'
    note += f'<p class="note">{E(cl["note"])}</p>' if cl.get("note") else ""
    return (f'<article class="card" id="{E(cl["id"])}" data-v="{vk}"><header><div><h3>{E(cl["topic"])} <span class="per">{E(cl["period"])}</span></h3>'
            f'<div class="tgt">Target: {E(target_text(cl["target"]))} · <a class="copy" href="#{E(cl["id"])}" data-copy>Copy link</a></div></div>'
            f'<span class="pill v-{vk}">{vl}</span></header>'
            f'{fold(said + result + resp + note)}</article>')

def fold(inner):
    return f'<details><summary>Quotes, source pages and working</summary>{inner}</details>'

def actual_text(cl, today):
    o = cl["outcome"]
    if "value" in o: return fmt(o["value"], o["unit"])
    if o.get("status") == "pending" or not o.get("quote"): return "—"
    return f'Done {dt.date.fromisoformat(o["first_seen"]).strftime("%b %Y")}' if o.get("done", True) else "Not yet"

def ledger(c, today):
    rows = ""
    for cl in c["claims"]:
        vk, vl = verdict(cl, today)
        rows += (f'<tr data-v="{vk}"><td><a href="#{E(cl["id"])}">{E(cl["topic"])}</a></td><td>{E(cl["period"])}</td>'
                 f'<td class="n">{E(target_text(cl["target"]))}</td><td class="n">{E(actual_text(cl, today))}</td>'
                 f'<td><span class="pill v-{vk}">{vl}</span></td><td>{cite(c, cl["said"][0])}</td></tr>')
    return ('<section class="ledger"><table><thead><tr><th>Promise</th><th>Period</th><th>Target</th><th>Actual</th>'
            f'<th>Verdict</th><th>First said</th></tr></thead><tbody>{rows}</tbody></table></section>'
            f'<p class="src dl"><a href="{c["symbol"].lower()}-promises.csv" download>Download this table (CSV)</a>, with quotes and page links.</p>')

def group(cl):
    t = cl["topic"].lower()
    if "margin" in t: return "Margins"
    if "working capital" in t: return "Working capital"
    if "revenue" in t and cl["target"]["kind"] != "milestone": return "Revenue"
    return "Milestones and other targets"

SHORT = {"EBITDA margin": "EBITDA", "PAT margin": "PAT", "Working capital days": "", "Revenue": ""}

def result_text(cl, today):
    vk, vl = verdict(cl, today)
    o, t = cl["outcome"], cl["target"]
    if "value" not in o:
        return f'{cl["topic"]}: {vl.lower()}'
    name = " ".join(x for x in (cl["period"], SHORT.get(cl["topic"], cl["topic"])) if x)
    if t["kind"] == "max":
        return f'{name} {fmt(o["value"], o["unit"])} vs ≤ {fmt(t["high"], t["unit"])}'
    return f'{name} {fmt(o["value"], o["unit"])} ({gap(cl).replace(" vs target", "").replace("-", "−")})'

def by_metric(c, today):
    rows = ""
    for g in ("Revenue", "Margins", "Working capital", "Milestones and other targets"):
        cls = [cl for cl in c["claims"] if group(cl) == g]
        due = [cl for cl in cls if verdict(cl, today)[0] != "pending"]
        kept = sum(verdict(cl, today)[0] == "met" for cl in due)
        res = "<br>".join(f'<a href="#{E(cl["id"])}" class="v-{verdict(cl, today)[0]}">{E(result_text(cl, today))}</a>' for cl in due) or "—"
        rows += (f'<tr><td>{g}</td><td class="n">{f"{kept} of {len(due)}" if due else "—"}</td><td>{res}</td>'
                 f'<td class="n">{len(cls) - len(due) or "—"}</td></tr>')
    return ('<section class="ledger metric"><table><thead><tr><th>Metric</th><th>Kept</th><th>Each due result vs first target</th>'
            f'<th>Still open</th></tr></thead><tbody>{rows}</tbody></table></section>')

def revenue_rows(c):
    return [cl for cl in c["claims"] if group(cl) == "Revenue" and "value" in cl["outcome"]]

def delivery(c):
    rows = revenue_rows(c)
    if not rows: return ""
    ratios = [cl["outcome"]["value"] / cl["target"]["low"] for cl in rows]
    avg = sum(ratios) / len(ratios)
    trs = "".join(f'<tr><td><a href="#{E(cl["id"])}">{E(cl["period"])}</a></td><td class="n">{E(target_text(cl["target"]))}</td>'
                  f'<td class="n">{fmt(cl["outcome"]["value"], "₹ cr")}</td><td class="n">{r*100:.0f}%</td></tr>' for cl, r in zip(rows, ratios))
    trs += f'<tr class="tot"><td>Average</td><td></td><td></td><td class="n">{avg*100:.0f}%</td></tr>'
    imp = ""
    fwd = next((cl for cl in c["claims"] if cl.get("implied")), None)
    if fwd:
        i = fwd["implied"]
        base = next(cl for cl in c["claims"] if cl["id"] == i["base"])
        b = base["outcome"]["value"]
        g = [m * i["multiple"] for m in i["market_growth_pct"]]
        lo, hi = (b * (1 + x / 100) for x in g)
        rng = lambda k: f'{fmt(lo * k, "₹ cr")}–{fmt(hi * k, "₹ cr")}'
        imp = (f'<h3>What {fwd["period"]} guidance implies</h3><table><tbody>'
               f'<tr><td>Guidance: <a href="#{E(fwd["id"])}">{E(target_text(fwd["target"]))}</a>. Market growth put at '
               f'{i["market_growth_pct"][0]}–{i["market_growth_pct"][1]}%, so {g[0]:g}–{g[1]:g}% on {base["period"]} audited {fmt(b, "₹ cr")}</td><td class="n">{rng(1)}</td></tr>'
               f'<tr><td>If delivered at the {len(rows)}-year average rate ({avg*100:.0f}%)</td><td class="n">{rng(avg)}</td></tr>'
               f'<tr><td>If delivered at the {rows[-1]["period"]} rate ({ratios[-1]*100:.0f}%)</td><td class="n">{rng(ratios[-1])}</td></tr></tbody></table>'
               f'<p class="src">Simple arithmetic on management\'s own numbers, to show what the track record means for the open target. '
               f'Not a forecast or a recommendation.</p>')
    return (f'<section class="panel deliv"><h2>How much of its revenue guidance gets delivered</h2>'
            f'<p class="src">Audited revenue as a share of the first revenue target (lower end of the range where a range was given).</p>'
            f'<table><thead><tr><th>Year</th><th class="n">First target</th><th class="n">Audited</th><th class="n">Delivered</th></tr></thead><tbody>{trs}</tbody></table>{imp}</section>')

def ledger_csv(c, today):
    f = io.StringIO()
    w = csv.writer(f)
    w.writerow(["promise", "period", "target", "actual", "verdict", "result_vs_first_target", "first_said_on", "first_said_page",
                "first_said_pdf", "speaker", "quote", "scorecard_link"])
    for cl in c["claims"]:
        s = cl["said"][0]
        w.writerow([cl["topic"], cl["period"], target_text(cl["target"]), actual_text(cl, today), verdict(cl, today)[1], gap(cl),
                     s["doc"], s["page"], f'{c["sources"][s["doc"]]["url"]}#page={s["page"]}', s.get("speaker", ""), s["quote"],
                     f'{SITE_URL}{c["symbol"].lower()}.html#{cl["id"]}'])
    return f.getvalue()

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
            f'<p class="src">Guidance: concall transcripts. Reported: audited consolidated results. Both cited in the cards below. FY = April–March.</p></section>')

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
FONTS = "Source+Serif+4:ital,wght@0,400;0,600;1,400&family=Source+Sans+3:wght@400;600;700"

def page(title, body, desc):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family={FONTS}&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><main>{body}</main>
<footer>Built by <a href="https://app.avanisai.com">Avanis</a>. Facts only: what management said on the record and what was later reported. Not investment advice. Spotted an error, or want a company added? <a href="mailto:{EMAIL}">{EMAIL}</a></footer>
<script>document.querySelectorAll('.filters button').forEach(b=>b.onclick=()=>{{document.querySelectorAll('.filters button').forEach(x=>x.classList.toggle('on',x===b));
document.querySelectorAll('[data-v]').forEach(c=>c.hidden=b.dataset.f!=='all'&&c.dataset.v!==b.dataset.f)}});
document.querySelectorAll('[data-copy]').forEach(a=>a.addEventListener('click',()=>{{navigator.clipboard?.writeText(location.origin+location.pathname+a.hash);a.textContent='Copied';setTimeout(()=>a.textContent='Copy link',1500)}}));
document.querySelectorAll('.watch li>a').forEach(a=>a.addEventListener('click',()=>document.querySelector('.filters button[data-f=all]').click()));
document.addEventListener('click',e=>{{const a=e.target.closest('a[href^="#"]');if(!a)return;history.replaceState({{y:scrollY}},'');if(a.hash===location.hash)setTimeout(openHash)}},true);
const openHash=()=>{{const c=location.hash&&document.getElementById(location.hash.slice(1));if(!c){{if(history.state)scrollTo(0,history.state.y);return}}if(c.hidden)document.querySelector('.filters button[data-f=all]').click();const d=c.querySelector('details');if(d)d.open=true;c.scrollIntoView()}};history.scrollRestoration='manual';addEventListener('hashchange',openHash);openHash()</script></body></html>"""

def fwd_csv(c):
    return ROOT / "checks" / f'{c["symbol"]}_forward_statements.csv'

def selection(c, n_calls):
    f = fwd_csv(c)
    if not f.exists(): return ""
    rows = list(csv.DictReader(f.open()))
    used = sum(bool(r["used_in_claim"]) for r in rows)
    return (f'<li><b>Checking for cherry-picking:</b> a script lists every sentence management said on the {n_calls} calls that contains a number '
            f'and a forward-looking word (will, expect, target, guidance, plan…): {len(rows)} sentences, {used} of them used here. '
            f'<a href="{f.name}" download>Download all {len(rows)}</a> to see what was left out and judge for yourself.</li>')

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
    calls = [k for k in c["sources"] if not is_audited(c, k)]
    n_aud = len(c["sources"]) - len(calls)
    first = min(calls); last = max(calls)
    body = f"""<nav><a href="index.html">← All companies</a></nav>
<section class="hero"><div class="eyebrow">{E(c["exchange"])}: {E(c["symbol"])}</div><h1>{E(c["name"])}</h1>
<p class="lede">Management kept <b>{n["met"]} of {scored}</b> promises that are due so far. Promises come from the company's concall transcripts and reported financials from its audited results, each linked to the exact page.</p>
<div class="stats">{stats}</div></section>
<h2 class="evid">By metric</h2>{by_metric(c, today)}
<h2 class="evid">Every promise</h2><div class="filters">{filters}</div>{ledger(c, today)}
{delivery(c)}
{watch_list(c, today)}
{revenue_chart(c)}
<h2 class="evid">Evidence for each promise</h2>{cards}
<section class="panel method"><h2>How this is built</h2><ul>
<li><b>Sources:</b> {len(calls)} earnings-call transcripts from {date_label(first)} to {date_label(last)} and {n_aud} audited annual results filings, all downloaded from <a href="{E(c["ir_page"])}">the company's investor page</a>. No third-party data.</li>
<li><b>Reported numbers:</b> revenue and margins are taken from the audited consolidated results (₹ million, converted to ₹ crore), with the working shown on each card. Revenue means revenue from operations, excluding other income. Working-capital days and milestones are not in audited results, so they come from what management said on the call.</li>
<li><b>What counts as a promise:</b> a specific, checkable number or milestone said by management (not by analysts) with a time frame.</li>
{selection(c, len(calls))}
<li><b>Verdict:</b> scored against the <i>first</i> guidance given. Later cuts are shown, not hidden. Delivered = met or beat the target. Late = milestone happened after the stated date, or not yet.</li>
<li><b>Checked by script:</b> every quote is tested word-for-word against the cited PDF page, and the speaker is checked against the transcript. Every audited number is checked to appear on the cited page of the filing.</li>
<li>Data as of {date_label(today)}. Spotted an error? Email <a href="mailto:{EMAIL}">{EMAIL}</a> or open an issue on GitHub.</li></ul></section>"""
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
<p class="lede">Free scorecards for Indian listed companies. What management guided on earnings calls, what the audited results show, and the exact page for both. No login, no API key.</p></section>
<section class="list">{rows}</section>"""
    return page("Avanis Promise Scorecard", body, "What Indian managements guided vs what they delivered, cited to the page.")

def main(symbols):
    OUT.mkdir(exist_ok=True)
    cos = [load_company(s) for s in symbols]
    for c in cos:
        (OUT / f"{c['symbol'].lower()}.html").write_text(company_page(c))
        (OUT / f"{c['symbol'].lower()}-promises.csv").write_text(ledger_csv(c, c["checked_on"]))
        if fwd_csv(c).exists(): shutil.copy(fwd_csv(c), OUT / fwd_csv(c).name)
    (OUT / "index.html").write_text(index_page(cos))
    print("built", [c["symbol"] for c in cos])

if __name__ == "__main__":
    main(sys.argv[1:] or [p.stem for p in (ROOT / "data/companies").glob("*.json") if "." not in p.stem])
