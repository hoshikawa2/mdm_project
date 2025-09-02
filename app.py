import asyncio, logging, time, json, httpx
from fastapi import FastAPI, HTTPException
from schemas import RequestPayload, ResponseTemplate
from services.address_service import parse_address
from services.normalize_service import normalize_customer
from services.dedupe_service import dedupe_candidates
from services.golden_service import pick_golden
from services.harmonize_service import harmonize
from services.enrich_service import enrich
from config import settings

app = FastAPI()
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("mdm.app")

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/llm/ping")
async def llm_ping():
    ep = settings.OLLAMA_ENDPOINTS[0]
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{ep}/api/tags")
            return {"endpoint": ep, "status": r.status_code}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama not reachable at {ep}: {e}")

@app.post("/mdm/process", response_model=ResponseTemplate)
async def process(payload: RequestPayload):
    t0 = time.time()
    logger.info(f"[STEP] domain={payload.domain} ops={payload.operations} records={len(payload.records)}")

    issues = []

    sem_n = asyncio.Semaphore(settings.CONCURRENCY_NORMALIZE)
    async def _n(r):
        try:
            async with sem_n:
                return await normalize_customer(r.model_dump())
        except Exception as e:
            issues.append({"stage":"normalize","id": getattr(r,'id',None),"error":str(e)})
            return {}

    norm = await asyncio.gather(*[_n(r) for r in payload.records])
    logger.info(f"[STEP] normalize done in {time.time()-t0:.2f}s")

    sem_a = asyncio.Semaphore(settings.CONCURRENCY_ADDRESS)
    async def _a(r):
        try:
            if r.get("address") or r.get("cep"):
                async with sem_a:
                    r["_parsed"] = await parse_address(r)
            return r
        except Exception as e:
            issues.append({"stage":"address","id": r.get('id'),"error":str(e)})
            return r

    norm = await asyncio.gather(*[_a(r) for r in norm])
    logger.info(f"[STEP] address-parse done in {time.time()-t0:.2f}s")

    matches = dedupe_candidates(norm)
    golden = pick_golden(norm) if any(op in payload.operations for op in ("consolidate","dedupe")) else None
    harm = harmonize(golden or {})
    enr = enrich(norm) if "enrich" in payload.operations else []

    return ResponseTemplate(
        record_clean=norm,
        golden_record=golden,
        matches=matches,
        harmonization=harm,
        enrichment=enr,
        issues=issues,
        actions=[],
        pii_masks={},
        audit_log=[],
        confidence=0.9 if golden else 0.7
    )
