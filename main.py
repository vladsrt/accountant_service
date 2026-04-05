from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routers.auth import router as auth_router
from app.api.routers.bank import router as bank_router
from app.api.routers.company import router as company_router
from app.api.routers.classification import router as classification_router
from app.api.routers.ksef import router as ksef_router
from app.api.routers.users import router as users_router
from app.core.limiter import limiter

app = FastAPI(
    title="Accountant Service API",
    description="API for KSeF integration and automated accounting",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(company_router, prefix="/api/v1")
app.include_router(ksef_router)
app.include_router(bank_router)
app.include_router(classification_router)


@app.get("/")
async def root():
    return {"status": "ok", "message": "Accountant Service is running!"}
