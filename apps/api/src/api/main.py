from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import cv, stats

app = FastAPI(title="SkillPolaris API")

# Dev-only: no auth in front of this API yet, and the browser calls it directly
# from the web app's origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stats.router)
app.include_router(cv.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
