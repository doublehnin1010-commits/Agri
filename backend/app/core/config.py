from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Agriculture AI Assistant"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    mongodb_uri: str
    mongodb_db_name: str = "agriculture_ai"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7

    chat_provider: str = "gemini"
    chat_model: str = Field(default="gemini-2.5-flash", validation_alias=AliasChoices("GEMINI_MODEL", "GEMINI_CHAT_MODEL", "CHAT_MODEL"))
    temperature: float = Field(default=0.2, validation_alias=AliasChoices("TEMPERATURE", "GEMINI_TEMPERATURE"))
    embedding_model: str = Field(default="local-hash", validation_alias=AliasChoices("EMBEDDING_MODEL", "GEMINI_EMBEDDING_MODEL"))
    local_embedding_dimensions: int = 768

    chroma_persist_dir: str = "./chroma_data"
    chroma_collection_name: str = "agriculture_documents"
    rag_top_k: int = Field(default=5, validation_alias=AliasChoices("TOP_K", "RAG_TOP_K"))
    rag_semantic_threshold: float = 0.0
    enable_lexical_search: bool = True
    lexical_cache: bool = True
    enable_metadata_filtering: bool = True
    enable_query_rewrite: bool = False
    rag_min_lexical_similarity: float = 0.25

    chunk_size: int = 1000
    chunk_overlap: int = 150
    max_upload_mb: int = 50
    max_image_upload_mb: int = 10
    gemini_vision_model: str = Field(default="gemini-2.5-flash", validation_alias=AliasChoices("GEMINI_VISION_MODEL", "GEMINI_MODEL", "CHAT_MODEL"))

    speech_max_upload_mb: int = 25
    ffmpeg_timeout_seconds: int = 30
    ffmpeg_path: str = "ffmpeg"
    edge_tts_myanmar_voice: str = "my-MM-NilarNeural"
    edge_tts_english_voice: str = "en-US-AriaNeural"
    edge_tts_rate: str = "+0%"
    tts_max_characters: int = 3000

    gemini_api_key: str = Field(default="", validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"))
    gemini_api_keys: str = Field(default="", validation_alias=AliasChoices("GEMINI_API_KEYS", "GOOGLE_API_KEYS"))
    gemini_chat_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_chat_fallback_model: str = "gemini-2.5-flash-lite"
    gemini_chat_timeout_seconds: int = 120
    gemini_chat_max_retries: int = 2
    gemini_chat_retry_base_seconds: float = 1.0
    gemini_stt_model: str = "gemini-2.5-flash"
    gemini_stt_fallback_model: str = "gemini-2.5-flash-lite"
    gemini_stt_timeout_seconds: int = 120
    gemini_stt_max_retries: int = 2
    gemini_stt_retry_base_seconds: float = 1.0
    admin_email: str = ""
    admin_password: str = ""
    creator_name: str = "Zarni Maung"
    creator_portfolio_url: str = "https://zarnimaung-portfolio.vercel.app/"

    @property
    def llm_temperature(self) -> float:
        return self.temperature

    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()



