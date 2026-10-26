"""Rebuild data/listings.json from a folder of exported find JSON files.

Usage: python3 scripts/build_listings.py <finds_dir> <updated_iso>
Each file in <finds_dir> is one ArtifactData document ({"id":..., "data":{...}} or a bare object).
Hidden finds are left out. Only http(s) links are kept.
"""
import glob, json, os, sys
from urllib.parse import urlparse

FIELDS = ["kind", "title", "org", "location", "pay", "deadline", "deadlineText", "source", "foundAt", "note"]

def main(src, updated):
    rows = []
    for p in sorted(glob.glob(os.path.join(src, "**", "*.json"), recursive=True)):
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        doc = d.get("data", d)
        if doc.get("hidden") or doc.get("kind") not in ("internship", "competition"):
            continue
        url = doc.get("url", "") or ""
        if url and urlparse(url).scheme not in ("http", "https"):
            url = ""
        row = {k: (doc.get(k) or "") for k in FIELDS}
        row["id"] = d.get("id") or os.path.basename(p)[:-5]
        row["url"] = url
        rows.append(row)
    out = os.path.join(os.path.dirname(__file__), "..", "data", "listings.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"updated": updated, "listings": rows}, f, ensure_ascii=False, indent=1)
    print(f"wrote {len(rows)} listings")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
