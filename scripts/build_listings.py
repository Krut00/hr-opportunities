"""Rebuild data/listings.json from a folder of exported find JSON files.

Usage: python3 scripts/build_listings.py <finds_dir> <updated_iso>
Each file in <finds_dir> is one ArtifactData document ({"id":..., "data":{...}} or a bare object).
Hidden finds are left out. Only http(s) links are kept.
"""
import csv, glob, json, os, sys
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
    # CSV copy for the Google Sheet (IMPORTDATA), soonest deadline first
    def key(r):
        return (r["kind"] != "internship", r["deadline"] or "9999-12-31", r["org"].lower())
    cpath = os.path.join(os.path.dirname(__file__), "..", "data", "listings.csv")
    with open(cpath, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Type", "Title", "Company / organiser", "Location", "Stipend / prize", "Apply by", "Source", "Note", "Link", "Found on"])
        today = updated[:10]
        for r in sorted(rows, key=key):
            if r["deadline"] and r["deadline"] < today:
                continue  # closed listings stay off the sheet
            w.writerow(["Internship" if r["kind"] == "internship" else "HR competition", r["title"], r["org"], r["location"],
                        r["pay"], r["deadline"] or r["deadlineText"], r["source"], r["note"], r["url"], (r["foundAt"] or "")[:10]])
    print(f"wrote {len(rows)} listings")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
