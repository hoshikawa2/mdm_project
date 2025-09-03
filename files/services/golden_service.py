def pick_golden(rows):
    if not rows: return {}
    def score(r): return (5 if r.get("source") in ("ERP","CRM") else 0) + sum(1 for v in r.values() if v not in (None,"",[],{}))
    best = max(rows, key=score)
    gold = dict(best)
    for r in rows:
        for k,v in r.items():
            if gold.get(k) in (None,"",[],{}) and v not in (None,"",[],{}):
                gold[k]=v
    return gold
