from fastapi import FastAPI
from src.routers import upload

app = FastAPI(title="MarkPulse AI", version="0.1.0")
app.include_router(upload.router)


@app.get("/health")
def health():
    return {"status": "ok"}