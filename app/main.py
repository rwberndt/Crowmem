from fastapi import FastAPI

from app.api.admin import router as admin_router
from app.api.beliefs import router as beliefs_router
from app.api.episodes import router as episodes_router
from app.api.events import router as events_router
from app.api.memories import router as memories_router
from app.api.outcomes import router as outcomes_router
from app.api.recall import router as recall_router
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="Corvid Memory Engine", version="0.1.0")

app.include_router(events_router)
app.include_router(memories_router)
app.include_router(recall_router)
app.include_router(outcomes_router)
app.include_router(admin_router)
app.include_router(beliefs_router)
app.include_router(episodes_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
