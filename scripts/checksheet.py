"""Write checks/<SYMBOL>.csv: one row per quote, for checking by hand against the source PDF."""
import csv, sys
import re
from common import ROOT, load_company, all_citations, page_text
from build import verdict, rule_text, target_text, fmt

def main(symbol):
    c = load_company(symbol)
    claims = {cl["id"]: cl for cl in c["claims"]}
    out = ROOT / "checks" / f"{symbol}.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["claim_id", "topic", "period", "row_type", "call_date", "pdf_page", "printed_page_label", "open_pdf_at_page",
                    "speaker", "exact_quote", "target", "reported_value", "verdict", "how_scored",
                    "checked_quote_ok (Y/N)", "checked_verdict_ok (Y/N)", "your_notes"])
        for cid, kind, cit in all_citations(c):
            cl = claims[cid]; o = cl["outcome"]
            url = c["sources"][cit["doc"]]["url"] + f"#page={cit['page']}"
            row_type = {"said": cit.get("role", "said"), "outcome": "reported", "response": "management_response", "context": "context"}[kind]
            m = re.search(r"Page \d+ of \d+", page_text(symbol, cit["doc"], cit["page"]))
            w.writerow([cid, cl["topic"], cl["period"], row_type, cit["doc"], cit["page"], m.group(0) if m else "", url,
                        cit.get("speaker", ""), cit["quote"], target_text(cl["target"]),
                        fmt(o["value"], o["unit"]) if "value" in o else o.get("status", ""),
                        verdict(cl, c["checked_on"])[1], rule_text(cl, c["checked_on"]), "", "", ""])
    print("wrote", out)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "KAYNES")
