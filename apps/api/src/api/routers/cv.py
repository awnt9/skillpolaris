from fastapi import APIRouter, HTTPException, UploadFile

router = APIRouter()

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


@router.post("/cv/upload")
async def upload_cv(file: UploadFile) -> dict[str, str]:
    if file.content_type != "application/pdf" or not (file.filename or "").lower().endswith(
        ".pdf"
    ):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    size = 0
    while chunk := await file.read(CHUNK_SIZE):
        size += len(chunk)
        if size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File exceeds the 10 MB limit.")

    return {"filename": file.filename or "resume.pdf", "status": "received"}
