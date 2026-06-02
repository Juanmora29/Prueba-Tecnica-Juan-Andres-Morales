import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL", "intfloat/multilingual-e5-small"
    )
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    top_k: int = int(os.getenv("TOP_K_RESULTS", "5"))
    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.4"))
    chroma_db_path: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    docs_dir: str = os.getenv("DOCS_DIR", "./docs")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    # Local fallback (Ollama)
    local_fallback_enabled: bool = os.getenv(
        "LOCAL_FALLBACK_ENABLED", "false"
    ).lower() in ("true", "1", "yes")
    local_model_name: str = os.getenv("LOCAL_MODEL_NAME", "llama3.2:3b")
    ollama_url: str = os.getenv(
        "OLLAMA_URL", "http://localhost:11434/api/generate"
    )


settings = Settings()
