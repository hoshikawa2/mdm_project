from rapidfuzz import fuzz

def _sim(a: str, b: str) -> float:
    if not a or not b: return 0.0
    return fuzz.token_set_ratio(a, b) / 100.0

def _pairs(n: int):
    for i in range(n):
        for j in range(i+1, n):
            yield i, j

def dedupe_candidates(rows, threshold=0.87):
    out = []
    for i,j in _pairs(len(rows)):
        a,b = rows[i], rows[j]
        s = (
            _sim(a.get("name",""), b.get("name","")) +
            max(_sim(a.get("email",""), b.get("email","")), _sim(a.get("phone",""), b.get("phone",""))) +
            _sim(a.get("address",""), b.get("address",""))
        ) / 3.0
        if s >= threshold:
            out.append({"i": i, "j": j, "score": round(s,3)})
    return out
