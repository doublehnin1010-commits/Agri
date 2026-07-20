from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8")

    app_name: str = "Myanmar Proverbs AI Tutor"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    mongodb_uri: str
    mongodb_db_name: str = "mm_proverbs_ai"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7

    ollama_base_url: str = Field(default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL")
    ollama_model: str = "qwen3:0.6b"
    chat_model: str = Field(default="qwen3:0.6b", validation_alias=AliasChoices("CHAT_MODEL", "OLLAMA_CHAT_MODEL"))
    utility_model: str = Field(default="qwen3:0.6b", validation_alias=AliasChoices("UTILITY_MODEL", "OLLAMA_UTILITY_MODEL"))
    ollama_fast_model: str = Field(default="qwen3:0.6b", validation_alias=AliasChoices("UTILITY_MODEL", "OLLAMA_FAST_MODEL"))
    ollama_complex_model: str = Field(default="qwen3:0.6b", validation_alias=AliasChoices("CHAT_MODEL", "OLLAMA_COMPLEX_MODEL"))
    ollama_timeout_seconds: int = Field(default=180, validation_alias=AliasChoices("OLLAMA_TIMEOUT", "OLLAMA_TIMEOUT_SECONDS"))
    utility_temperature: float = Field(default=0.1, validation_alias=AliasChoices("UTILITY_TEMPERATURE", "OLLAMA_UTILITY_TEMPERATURE"))
    utility_num_predict: int = Field(default=128, validation_alias=AliasChoices("UTILITY_NUM_PREDICT", "OLLAMA_UTILITY_NUM_PREDICT"))
    utility_num_ctx: int = Field(default=2048, validation_alias=AliasChoices("UTILITY_NUM_CTX", "OLLAMA_UTILITY_NUM_CTX"))
    chat_temperature: float = Field(default=0.3, validation_alias=AliasChoices("CHAT_TEMPERATURE", "OLLAMA_CHAT_TEMPERATURE"))
    chat_num_predict: int = Field(default=160, validation_alias=AliasChoices("CHAT_NUM_PREDICT", "OLLAMA_CHAT_NUM_PREDICT"))
    chat_num_ctx: int = Field(default=2048, validation_alias=AliasChoices("CHAT_NUM_CTX", "OLLAMA_CHAT_NUM_CTX"))
    fast_response_mode: bool = True
    fast_chat_model: str = Field(default="qwen3:0.6b", validation_alias=AliasChoices("FAST_CHAT_MODEL", "OLLAMA_FAST_CHAT_MODEL"))
    ollama_num_predict: int = 128
    ollama_complex_num_predict: int = 512
    temperature: float = Field(
        default=0.0,
        validation_alias=AliasChoices("TEMPERATURE", "OLLAMA_TEMPERATURE"),
    )

    embedding_model: str = "bge-m3"

    metadata_batch_size: int = 5
    metadata_max_concurrent: int = 2
    metadata_max_retries: int = 3

    chroma_persist_dir: str = "./chroma_data"
    chroma_collection_name: str = "proverbs"

    enable_query_rewrite: bool = False
    enable_lexical_search: bool = True
    enable_metadata_filtering: bool = True
    lexical_cache: bool = True
    rag_top_k: int = 2
    rag_min_relevance_score: float = 0.5
    rag_min_lexical_similarity: float = 0.5
    rag_semantic_threshold: float = 0.5

    whisper_model: str = "base"
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"
    whisper_beam_size: int = 5
    whisper_vad_silence_ms: int = 500
    whisper_local_files_only: bool = True
    preload_whisper: bool = True
    speech_max_upload_mb: int = 25
    ffmpeg_timeout_seconds: int = 30
    ffmpeg_path: str = "ffmpeg"
    edge_tts_myanmar_voice: str = "my-MM-NilarNeural"
    edge_tts_english_voice: str = "en-US-AriaNeural"
    edge_tts_rate: str = "+0%"
    tts_max_characters: int = 3000

    admin_email: str = ""

    @property
    def llm_temperature(self) -> float:
        return self.temperature

    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

settings = Settings()
