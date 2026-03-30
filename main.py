from fastapi import FastAPI

from app.api.routers.ksef import router as ksef_router

app = FastAPI(
    title="Accountant Service API",
    description="API for KSeF integration and automated accounting",
    version="1.0.0",
)

app.include_router(ksef_router)


@app.get("/")
async def root():
    return {"status": "ok", "message": "Accountant Service is running!"}
