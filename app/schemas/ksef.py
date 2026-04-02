"""Pydantic schemas for KSeF API endpoints."""

from pydantic import BaseModel, Field


class KsefSetupRequest(BaseModel):
    """Schema for setting up a company's KSeF credentials."""

    nip: str = Field(..., min_length=10, max_length=10, description="The 10-digit NIP")
    ksef_token: str = Field(..., description="The highly sensitive raw KSeF authorization token")
