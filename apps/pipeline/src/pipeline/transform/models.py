from typing import Any

from pydantic import BaseModel, Field, Json


class JobOfferMetadata(BaseModel):
    standart_position: str = Field(
        ...,
        description=(
            "Standarized role, for example 'Data Engineer' or 'Project Manager'. "
            "Analyze context to normalize noisy titles."
        ),
    )
    hard_skills: list[str] = Field(
        default_factory=list,
        description=(
            "Technical skills, tools, or methodologies. Each entry must be 1-3 words "
            "and appear literally in the text."
        ),
    )
    is_remote: bool = Field(
        description="True if the job description explicitly mentions remote or hybrid work."
    )
    language_required: str | None = Field(
        None,
        description=(
            "Primary language required for the role. Use English names like Spanish, "
            "French, or English. Return null if not specified."
        ),
    )


class RawJobOffer(BaseModel):
    id: int
    source: str
    job_id: str
    raw_content: Json[dict[str, Any]]
    keyword: str | None = None


class CleanJobOffer(BaseModel):
    id: int
    source: str
    job_id: str
    title: str
    description: str
    keyword: str | None = None


class EmbeddedJobOffer(BaseModel):
    id: int
    source: str
    job_id: str
    title: str
    description: str
    keyword: str | None
    vector: list[float]
    metadata: JobOfferMetadata

    def to_payload(self) -> dict[str, Any]:
        return {
            "staging_id": self.id,
            "source": self.source,
            "job_id": self.job_id,
            "title": self.title,
            "description": self.description,
            "keyword": self.keyword,
            "standart_position": self.metadata.standart_position,
            "hard_skills": self.metadata.hard_skills,
            "is_remote": self.metadata.is_remote,
            "language": self.metadata.language_required,
        }
