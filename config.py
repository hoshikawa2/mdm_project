from pydantic import BaseModel
from typing import List
import os

class Settings(BaseModel):
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8001"))
    OLLAMA_ENDPOINTS: List[str] = [e.strip() for e in os.getenv("OLLAMA_ENDPOINTS","http://localhost:11434").split(",") if e.strip()]
    MODEL_ADDRESS: str = os.getenv("MODEL_ADDRESS", "qwen2.5:7b")
    MODEL_NORMALIZE: str = os.getenv("MODEL_NORMALIZE", "qwen2.5:7b")
    NUM_GPU: int = int(os.getenv("NUM_GPU", "22"))
    NUM_BATCH: int = int(os.getenv("NUM_BATCH", "512"))
    NUM_CTX: int = int(os.getenv("NUM_CTX", "4096"))
    NUM_THREAD: int = int(os.getenv("NUM_THREAD", "16"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.0"))
    TOP_P: float = float(os.getenv("TOP_P", "1.0"))
    TOP_K: int = int(os.getenv("TOP_K", "40"))
    REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT", "180"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL","INFO")
    CONCURRENCY_NORMALIZE: int = int(os.getenv("CONCURRENCY_NORMALIZE","8"))
    CONCURRENCY_ADDRESS: int = int(os.getenv("CONCURRENCY_ADDRESS","8"))
    # Optional: best-effort postal lookup (disabled by default)
    USE_POSTAL_LOOKUP: bool = os.getenv("USE_POSTAL_LOOKUP","0") in ("1","true","True")
    ZIPCODEBASE_KEY: str = os.getenv("ZIPCODEBASE_KEY","")
settings = Settings()
