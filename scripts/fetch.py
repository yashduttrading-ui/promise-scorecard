"""Download every cited source PDF from the company's own IR site and check its sha256."""
import hashlib, subprocess, sys
from common import RAW, load_company

def main(symbol):
    c = load_company(symbol)
    RAW.mkdir(exist_ok=True)
    for key, s in c["sources"].items():
        out = RAW / s["file"]
        if not out.exists():
            subprocess.run(["curl", "-sfL", "-A", "Mozilla/5.0", "-o", str(out), s["url"]], check=True)
        h = hashlib.sha256(out.read_bytes()).hexdigest()
        print(("OK  " if h == s["sha256"] else "HASH CHANGED ") + s["file"])

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "KAYNES")
