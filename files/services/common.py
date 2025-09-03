import json, logging

logger = logging.getLogger("mdm.services")

def safe_json_from_text(text: str):
    try:
        return json.loads(text)
    except Exception:
        pass
    first = text.find("{"); last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        chunk = text[first:last+1]
        try:
            return json.loads(chunk)
        except Exception:
            pass
    last_ok = None
    for line in text.splitlines():
        line=line.strip()
        if not line or not line.startswith("{"): continue
        try:
            last_ok = json.loads(line)
        except Exception:
            continue
    return last_ok or {}
