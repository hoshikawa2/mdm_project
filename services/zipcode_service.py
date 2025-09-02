# services/zipcode_service.py
import os, asyncio, time, random, httpx, logging
from typing import Dict, Any

logger = logging.getLogger("services.zipcode_service")

ZIPCODEBASE_KEY = os.getenv("ZIPCODEBASE_KEY", "")
ZIPCODEBASE_URL = "https://app.zipcodebase.com/api/v1/search"

# Cache simples em memória (poderia ser LRU/Redis)
_ZIP_CACHE: Dict[str, Dict[str, Any]] = {}
# "In-flight" para coalescer chamadas concorrentes do mesmo CEP
_INFLIGHT: Dict[str, asyncio.Future] = {}
# Limitar concorrência global das chamadas externas
_SEM = asyncio.Semaphore(int(os.getenv("ZIPCODEBASE_MAX_CONCURRENCY", "4")))

def _norm_cep(cep: str) -> str:
    if not cep:
        return ""
    d = "".join(c for c in cep if c.isdigit())
    return d

async def _via_cep(cep_digits: str) -> Dict[str, Any]:
    """Fallback grátis BR (sem limites agressivos)."""
    url = f"https://viacep.com.br/ws/{cep_digits}/json/"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            if r.status_code != 200:
                logger.warning(f"[ViaCEP] status={r.status_code} for {cep_digits}")
                return {}
            data = r.json()
            if data.get("erro"):
                return {}
            # Formata postal_code no padrão 00000-000
            pc = f"{cep_digits[:5]}-{cep_digits[5:]}" if len(cep_digits) == 8 else None
            return {
                "thoroughfare": None,
                "house_number": None,
                "neighborhood": data.get("bairro"),
                "city": data.get("localidade"),
                "state": data.get("uf"),
                "postal_code": pc,
                "country_code": "BR",
                "complement": None
            }
    except Exception as e:
        logger.error(f"[ViaCEP] error for {cep_digits}: {e}")
        return {}

async def _zipcodebase_lookup(cep_digits: str, country: str) -> Dict[str, Any]:
    """Consulta Zipcodebase com retry/backoff e respeito a Retry-After."""
    params = {"codes": cep_digits, "country": country, "apikey": ZIPCODEBASE_KEY}
    retries = 3
    base_delay = float(os.getenv("ZIPCODEBASE_BASE_DELAY", "1.0"))

    timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, retries + 1):
            try:
                r = await client.get(ZIPCODEBASE_URL, params=params)
                if r.status_code == 429:
                    # Respeita Retry-After se existir
                    ra = r.headers.get("Retry-After")
                    if ra:
                        try:
                            wait_s = int(ra)
                        except ValueError:
                            wait_s = base_delay * attempt
                    else:
                        wait_s = base_delay * attempt
                    # Jitter leve para evitar sincronização
                    wait_s += random.uniform(0, 0.5)
                    logger.warning(f"[Zipcodebase] 429 on {cep_digits}, attempt {attempt}/{retries}, sleeping {wait_s:.2f}s")
                    await asyncio.sleep(wait_s)
                    continue

                r.raise_for_status()
                data = r.json()
                results = (data.get("results") or {}).get(cep_digits, [])
                if not results:
                    return {}
                enriched = results[0]
                # Monta saída mínima estável (Zipcodebase varia por plano)
                return {
                    "thoroughfare": enriched.get("street") or None,
                    "house_number": None,
                    "neighborhood": enriched.get("district") or None,
                    "city": enriched.get("city") or None,
                    "state": (enriched.get("state_code") or enriched.get("state")) or None,
                    "postal_code": f"{cep_digits[:5]}-{cep_digits[5:]}" if len(cep_digits) == 8 else cep_digits,
                    "country_code": country.upper(),
                    "complement": None
                }
            except httpx.HTTPStatusError as e:
                # Para 4xx (exceto 429) não adianta muito retry
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    logger.error(f"[Zipcodebase] {e.response.status_code} for {cep_digits}: {e.response.text[:200]}")
                    return {}
                # Para 5xx tenta novamente
                wait_s = base_delay * attempt + random.uniform(0, 0.5)
                logger.warning(f"[Zipcodebase] {e.response.status_code} retry {attempt}/{retries} in {wait_s:.2f}s")
                await asyncio.sleep(wait_s)
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                wait_s = base_delay * attempt + random.uniform(0, 0.5)
                logger.warning(f"[Zipcodebase] network {type(e).__name__} retry {attempt}/{retries} in {wait_s:.2f}s")
                await asyncio.sleep(wait_s)
            except Exception as e:
                logger.error(f"[Zipcodebase] unexpected error: {e}")
                return {}
    return {}

async def enrich_address_with_zipcode(record: Dict[str, Any]) -> Dict[str, Any]:
    """Enriquece record['_parsed'] via Zipcodebase com cache, coalescência e fallback ViaCEP."""
    cep_digits = _norm_cep(record.get("cep", ""))
    country = (record.get("country_code") or "BR").upper()

    if not cep_digits or len(cep_digits) < 5:
        return record

    # 1) cache hit
    if cep_digits in _ZIP_CACHE:
        record["_parsed"] = _ZIP_CACHE[cep_digits]
        return record

    # 2) coalescer chamadas concorrentes do mesmo CEP
    #    (quem chegar depois aguarda a futura resposta da primeira chamada)
    fut = _INFLIGHT.get(cep_digits)
    if fut:
        try:
            parsed = await fut
            if parsed:
                _ZIP_CACHE[cep_digits] = parsed
                record["_parsed"] = parsed
            return record
        except Exception:
            # Se a future falhou, vamos tentar nós mesmos
            pass

    # 3) primeira thread: cria a future e executa consulta sob semáforo
    loop = asyncio.get_running_loop()
    _INFLIGHT[cep_digits] = loop.create_future()

    try:
        async with _SEM:
            parsed = {}
            if ZIPCODEBASE_KEY:
                parsed = await _zipcodebase_lookup(cep_digits, country)

            # Fallback a ViaCEP se Zipcodebase falhar/limitar
            if not parsed and country == "BR":
                parsed = await _via_cep(cep_digits)

            # Guarda no cache
            if parsed:
                _ZIP_CACHE[cep_digits] = parsed

            # Resolve as esperas coalescidas
            if not _INFLIGHT[cep_digits].done():
                _INFLIGHT[cep_digits].set_result(parsed)

            if parsed:
                record["_parsed"] = parsed
            return record
    except Exception as e:
        logger.error(f"[Zip] enrich error for {cep_digits}: {e}")
        if cep_digits in _INFLIGHT and not _INFLIGHT[cep_digits].done():
            _INFLIGHT[cep_digits].set_result({})
        return record
    finally:
        # Limpa a chave de in-flight (evita vazamento)
        _INFLIGHT.pop(cep_digits, None)
