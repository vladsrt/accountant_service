from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Strong password, at least 8 characters")


class UserResponse(UserBase):
    id: int
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDeleteRequest(BaseModel):
    """Schema for confirming account deletion."""

    password: str = Field(..., description="Confirm password to delete account")
