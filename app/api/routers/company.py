from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db
from app.db.models.company import Company
from app.db.models.user import User
from app.schemas.company import CompanyCreate, CompanyResponse
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/company", tags=["company"])


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    company_data: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new company profile linked to the current user.
    """
    # Check if user already has a company
    result = await db.execute(select(Company).where(Company.user_id == current_user.id))
    existing_company = result.scalars().first()
    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already has a company profile"
        )

    # Check if NIP is already registered
    nip_result = await db.execute(select(Company).where(Company.nip == company_data.nip))
    if nip_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Company with this NIP already exists"
        )

    new_company = Company(user_id=current_user.id, nip=company_data.nip, ksef_token=None)
    db.add(new_company)
    await db.commit()
    await db.refresh(new_company)

    return new_company


@router.get("/me", response_model=CompanyResponse)
async def get_my_company(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve the current user's company profile.
    """
    result = await db.execute(select(Company).where(Company.user_id == current_user.id))
    company = result.scalars().first()

    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    return company
