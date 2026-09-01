from fastapi import APIRouter, HTTPException, UploadFile

from api.config import get_settings
from api.db import get_engine
from api.schemas.cv import CVMatchResponse, MatchedSkillOut, RoleMatchOut
from api.services.cv_extractor import CVSkillExtractor
from api.services.matching import match_cv_to_roles
from api.services.pdf import extract_text
from api.services.skills import normalized_skills

router = APIRouter()

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
TOP_N_ROLES = 5


@router.post("/cv/upload", response_model=CVMatchResponse)
async def upload_cv(file: UploadFile) -> CVMatchResponse:
    if file.content_type != "application/pdf" or not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(CHUNK_SIZE):
        size += len(chunk)
        if size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File exceeds the 10 MB limit.")
        chunks.append(chunk)

    resume_text = extract_text(b"".join(chunks))
    if not resume_text:
        raise HTTPException(status_code=422, detail="Could not extract any text from the PDF.")

    settings = get_settings()
    extractor = CVSkillExtractor(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )
    profile = await extractor.extract(resume_text)
    candidate_names = normalized_skills(profile.hard_skills)

    engine = get_engine()
    result = match_cv_to_roles(engine, candidate_names, top_n=TOP_N_ROLES)

    return CVMatchResponse(
        matched_skills=result.matched_skills,
        unmatched_skills=result.unmatched_skills,
        roles=[
            RoleMatchOut(
                standard_role=role.standard_role,
                score=role.score,
                job_count=role.job_count,
                is_remote_pct=role.is_remote_pct,
                language_distribution=role.language_distribution,
                matched_skills=[
                    MatchedSkillOut(name=skill.name, market_pct=skill.market_pct)
                    for skill in role.matched_skills
                ],
            )
            for role in result.roles
        ],
    )
