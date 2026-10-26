import csv, json, re, os, sys, collections, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from recruiters import SOURCES
from match import ALIAS, GROUPS, norm

final = json.load(open('final.json'))         # {code: [name, mcap, sector, industry, igroup, city, state, url, isin]}
OUT = '/home/claude/hr-opportunities/data/companies'
os.makedirs(OUT, exist_ok=True)
CAP = 500

# recruiter -> list of source keys
rec_src = collections.defaultdict(list)
for key, (label, url, summer, names) in SOURCES.items():
    for n in [x.strip() for x in names.split(',') if x.strip()]:
        rec_src[n].append(key)

HR_KEYS = {k for k in SOURCES if 'HR' in k}
by_code = {}            # code -> set of (recruiter, srckeys)
matched_rec = {}        # recruiter -> company name matched
names = {c: norm(v[0]) for c, v in final.items()}
for rec, keys in rec_src.items():
    pat = ALIAS.get(rec, 'AUTO')
    if pat is None: continue
    if rec in GROUPS:
        rx = re.compile(GROUPS[rec])
        hits = [c for c, n in names.items() if rx.search(n)]
        for c in hits: by_code.setdefault(c, []).append((rec + ' (group)', keys))
        if hits: matched_rec[rec] = f'{len(hits)} listed group companies'
        continue
    if pat == 'AUTO':
        pat = '^' + re.escape(norm(rec)) + r'\b'
    rx = re.compile(pat)
    hits = [c for c, n in names.items() if rx.search(n)]
    if hits:
        best = max(hits, key=lambda c: final[c][1])   # biggest match (avoids tiny namesakes)
        by_code.setdefault(best, []).append((rec, keys))
        matched_rec[rec] = final[best][0]

def label(keys):
    return '; '.join(sorted({SOURCES[k][0] for k in keys}))

def gsearch(name):
    q = re.sub(r'\b(ltd|limited)\.?$', '', name, flags=re.I).strip() + ' careers internship'
    return 'https://www.google.com/search?q=' + urllib.parse.quote_plus(q)

def site(u):
    u = (u or '').strip()
    if not u or u in ('-', 'NA'): return ''
    if not u.startswith('http'): u = 'https://' + u.lstrip('/')
    return u

HEAD = ['Rank in sector', 'Company', 'Industry', 'Sub-industry', 'Market cap (₹ crore)', 'HQ city', 'State',
        'Known MBA summer / campus recruiter?', 'Seen in (published placement reports)', 'Website', 'Careers search', 'BSE code']
sectors = collections.defaultdict(list)
for c, v in final.items():
    sec = v[2] or 'Unclassified'
    sectors[sec].append(c)

summary = []
for sec, codes in sectors.items():
    codes.sort(key=lambda c: -final[c][1])
    top = codes[:CAP]
    fn = re.sub(r'[^a-z0-9]+', '-', sec.lower()).strip('-') + '.csv'
    with open(os.path.join(OUT, fn), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(HEAD)
        for i, c in enumerate(top, 1):
            n, m, s, ind, grp, city, state, url, isin = final[c]
            hits = by_code.get(c, [])
            known = ''
            if hits:
                summer = any(SOURCES[k][2] for _, ks in hits for k in ks)
                grp_only = all(r.endswith('(group)') for r, _ in hits)
                hr = any(k in HR_KEYS for _, ks in hits for k in ks)
                known = ('Yes – HR roles' if hr else 'Yes') if not grp_only else 'Group-level (' + ', '.join(r[:-8] for r, _ in hits) + ')'
                if not summer and not grp_only: known += ' (final placements)'
            seen = label([k for _, ks in hits for k in ks]) if hits else ''
            w.writerow([i, n, ind, grp, m, city.title() if city.isupper() else city, state, known, seen, site(url), gsearch(n), c])
    summary.append((sec, len(codes), len(top), sum(1 for c in top if c in by_code), fn))

summary.sort(key=lambda x: -x[1])
json.dump(summary, open('summary.json', 'w'))

# recruiter tab
with open(os.path.join(OUT, 'mba-recruiters.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['Recruiter (as published)', 'Hired for HR roles (HRM programme lists)?', 'Seen in (published placement reports)', 'Listed in India as', 'Careers search'])
    for rec in sorted(rec_src, key=lambda r: (-len(rec_src[r]), r.lower())):
        keys = rec_src[rec]
        w.writerow([rec, 'Yes' if any(k in HR_KEYS for k in keys) else '', label(keys),
                    matched_rec.get(rec, 'Not listed / not matched'), gsearch(rec)])
for s in summary: print(s)
print('recruiters', len(rec_src), 'matched', len(matched_rec))
