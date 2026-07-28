import re

from pipeline.transform.models import CleanJobOffer, RawJobOffer


def clean_api_job_description(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""

    text = re.sub(r"http[s]?://\S+", "", text)
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", "", text)
    text = re.sub(r"#{2,}", "", text)
    text = re.sub(r"-{3,}", "", text)
    text = re.sub(r"\*{3,}", "", text)
    text = re.sub(r"\n\s*[\*\-]\s+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def preprocess_job_offer(raw_job: RawJobOffer) -> CleanJobOffer:
    raw_content = raw_job.raw_content

    # New canonical staging payload produced by extractors.
    if "title_raw" in raw_content and "description_raw" in raw_content:
        title = raw_content["title_raw"]
        description = raw_content["description_raw"]
    else:
        # Backward compatibility for already staged legacy records.
        match raw_job.source:
            case "SwissJobRoomExtractor":
                title = raw_content["jobContent"]["jobDescriptions"][0]["title"]
                description = raw_content["jobContent"]["jobDescriptions"][0]["description"]

            case "FranceTravailExtractor":
                title = raw_content["intitule"]
                description = raw_content["description"]

            case "USAJOBExtractor":
                descriptor = raw_content["SearchResult"]["SearchResultItems"][0][
                    "MatchedObjectDescriptor"
                ]
                title = descriptor["PositionTitle"]
                description = descriptor["QualificationSummary"]

            case _:
                raise ValueError(f"Unsupported source: {raw_job.source}")

    return CleanJobOffer(
        id=raw_job.id,
        source=raw_job.source,
        job_id=raw_job.job_id,
        title=title,
        description=clean_api_job_description(description),
        keyword=raw_job.keyword,
    )
