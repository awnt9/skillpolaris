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

    max_total_details: int = Field(alias="MAX_TOTAL_DETAILS")
    max_depth: int = Field(alias="MAX_DEPTH")
    extract_keyword_limit: int = Field(alias="EXTRACT_KEYWORD_LIMIT")
    extract_keyword_cooldown_hours: int = Field(alias="EXTRACT_KEYWORD_COOLDOWN_HOURS")

    transform_batch_size: int = Field(alias="TRANSFORM_BATCH_SIZE")
    filter_batch_size: int = Field(alias="FILTER_BATCH_SIZE")

    model: str = Field(alias="LLM_MODEL")
    ollama_base_url: str = Field(alias="OLLAMA_BASE_URL")
    ollama_api_key: str = Field(alias="OLLAMA_API_KEY")
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
