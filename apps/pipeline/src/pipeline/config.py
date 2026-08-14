from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pipeline settings loaded from environment / .env. All fields are required."""

    db_host: str = Field(alias="DB_HOST")
    db_port: int = Field(alias="DB_PORT")
    postgres_db: str = Field(alias="POSTGRES_DB")
    postgres_user: str = Field(alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")

    france_travail_client_id: str = Field(alias="FRANCE_TRAVAIL_CLIENT_ID")
    france_travail_client_secret: str = Field(alias="FRANCE_TRAVAIL_CLIENT_SECRET")
    france_travail_page_size: int = Field(
        alias="FRANCE_TRAVAIL_PAGE_SIZE",
        ge=1,
        le=150,
    )

    max_total_details: int = Field(alias="MAX_TOTAL_DETAILS")
    max_depth: int = Field(alias="MAX_DEPTH")
    extract_keyword_limit: int = Field(alias="EXTRACT_KEYWORD_LIMIT")
    extract_keyword_cooldown_hours: int = Field(alias="EXTRACT_KEYWORD_COOLDOWN_HOURS")

    transform_batch_size: int = Field(alias="TRANSFORM_BATCH_SIZE")
    filter_batch_size: int = Field(alias="FILTER_BATCH_SIZE")
    filter_min_description_chars: int = Field(
        alias="FILTER_MIN_DESCRIPTION_CHARS",
        ge=1,
    )
    filter_llm_excerpt_chars: int = Field(
        alias="FILTER_LLM_EXCERPT_CHARS",
        ge=100,
    )
    filter_llm_confidence: float = Field(
        alias="FILTER_LLM_CONFIDENCE",
        ge=0.0,
        le=1.0,
    )
    filter_llm_model: str = Field(alias="FILTER_LLM_MODEL")

    so_tag_pages: int = Field(alias="SO_TAG_PAGES")
    so_min_count: int = Field(alias="SO_MIN_COUNT")
    so_api_key: str | None = Field(alias="SO_API_KEY")

    # Comma-separated Greenhouse board tokens (e.g. "figma,stripe").
    greenhouse_board_tokens: str = Field(alias="GREENHOUSE_BOARD_TOKENS")

    # Chat (filter gate + transform metadata). OpenAI-compatible endpoint.
    llm_base_url: str = Field(alias="LLM_BASE_URL")
    llm_api_key: str = Field(alias="LLM_API_KEY")
    llm_model: str = Field(alias="LLM_MODEL")

    # Embeddings (Qdrant). Independent OpenAI-compatible endpoint.
    embedding_base_url: str = Field(alias="EMBEDDING_BASE_URL")
    embedding_api_key: str = Field(alias="EMBEDDING_API_KEY")
    embedding_model: str = Field(alias="EMBEDDING_MODEL")

    qdrant_host: str = Field(alias="QDRANT_HOST")
    qdrant_port: int = Field(alias="QDRANT_PORT")
    qdrant_collection_name: str = Field(alias="QDRANT_COLLECTION_NAME")
    qdrant_vector_size: int = Field(alias="QDRANT_VECTOR_SIZE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_configuration() -> Settings:
    try:
        return Settings()
    except Exception as e:
        print(f"Error on configuration: \n{e}")
        raise
