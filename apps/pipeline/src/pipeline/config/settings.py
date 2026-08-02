from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pipeline settings loaded from environment / .env."""

    # --- DATABASE ---
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    postgres_db: str = Field(alias="POSTGRES_DB")
    postgres_user: str = Field(alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")

    # --- USAJOBS ---
    usajobs_api_key: str = Field(alias="USAJOBS_API_KEY")
    usajobs_email: str = Field(alias="USAJOBS_EMAIL")

    # --- FRANCE TRAVAIL ---
    france_travail_client_id: str = Field(alias="FRANCE_TRAVAIL_CLIENT_ID")
    france_travail_client_secret: str = Field(alias="FRANCE_TRAVAIL_CLIENT_SECRET")

    # --- EXTRACTORS ---
    max_total_details: int = Field(alias="MAX_TOTAL_DETAILS")
    max_depth: int = Field(alias="MAX_DEPTH")

    # --- TRANSFORM ---
    transform_batch_size: int = Field(default=25, alias="TRANSFORM_BATCH_SIZE")

    # --- LLM ---
    model: str = Field(alias="LLM_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434/v1", alias="OLLAMA_BASE_URL")
    ollama_api_key: str = Field(default="ollama", alias="OLLAMA_API_KEY")
    embedding_model: str = Field(default="nomic-embed-text", alias="EMBEDDING_MODEL")

    # --- QDRANT ---
    qdrant_host: str = Field(default="localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    qdrant_collection_name: str = Field(default="job_offers", alias="QDRANT_COLLECTION_NAME")
    qdrant_vector_size: int = Field(default=768, alias="QDRANT_VECTOR_SIZE")

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
