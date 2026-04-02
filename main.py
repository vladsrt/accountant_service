from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routers.auth import router as auth_router
from app.api.routers.bank import router as bank_router
from app.api.routers.company import router as company_router
from app.api.routers.ksef import router as ksef_router
from app.core.limiter import limiter

app = FastAPI(
    title="Accountant Service API",
    description="API for KSeF integration and automated accounting",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(company_router, prefix="/api/v1")
app.include_router(ksef_router)
app.include_router(bank_router)


@app.get("/")
async def root():
    return {"status": "ok", "message": "Accountant Service is running!"}
