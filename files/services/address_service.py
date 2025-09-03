import httpx, json, itertools, logging, time, asyncio, re
from pathlib import Path
from files.config import settings
from .common import safe_json_from_text

logger = logging.getLogger("mdm.services")
_rr = itertools.count()

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "prompts" / "address_prompt.txt"

def _ep():
    return settings.OLLAMA_ENDPOINTS[next(_rr)%len(settings.OLLAMA_ENDPOINTS)]

async def parse_address(record: dict) -> dict:
    prompt = PROMPT_PATH.read_text(encoding="utf-8").replace("{input_json}", json.dumps(record, ensure_ascii=False))
    payload = {
        "model": settings.MODEL_ADDRESS,
        "prompt": prompt,
        "format": "json",
        "options": {
            "num_ctx": settings.NUM_CTX,
            "num_batch": settings.NUM_BATCH,
            "num_gpu": settings.NUM_GPU,
            "num_thread": settings.NUM_THREAD,
            "temperature": settings.TEMPERATURE
        },
        "stream": False
    }
    ep = _ep()
    timeout = httpx.Timeout(connect=5.0, read=float(settings.REQUEST_TIMEOUT), write=30.0, pool=5.0)
    async with httpx.AsyncClient(timeout=timeout) as c:
        last_exc = None
        for attempt in range(1,4):
            try:
                t0=time.time()
                r = await c.post(f"{ep}/api/generate", json=payload)
                dt=time.time()-t0
                logger.info(f"[LLM] address status={r.status_code} time={dt:.2f}s ep={ep} attempt={attempt}")
                r.raise_for_status()
                data = safe_json_from_text(r.text)
                resp = (data.get("response","{}") if isinstance(data, dict) else "{}").strip()
                out = json.loads(resp)
                if isinstance(out, dict):
                    # canonicalize BR CEP if model returned '00000000'
                    if out.get("postal_code") and re.fullmatch(r"\d{8}", out["postal_code"]):
                        out["postal_code"] = out["postal_code"][:5] + "-" + out["postal_code"][5:]
                    return out
                return {
                    "thoroughfare": None,"house_number": None,"neighborhood": None,"city": None,"state": None,"postal_code": None,"country_code": None,"complement": None
                }
            except Exception as e:
                last_exc = e
                logger.warning(f"[LLM] address attempt {attempt}/3 failed: {e}")
        logger.error(f"[LLM] address failed after retries: {last_exc}")
        return {"thoroughfare": None,"house_number": None,"neighborhood": None,"city": None,"state": None,"postal_code": None,"country_code": None,"complement": None}
