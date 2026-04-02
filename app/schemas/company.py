from pydantic import BaseModel, ConfigDict, field_validator


class CompanyBase(BaseModel):
    nip: str


class CompanyCreate(CompanyBase):
    @field_validator("nip")
    @classmethod
    def validate_nip(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 10:
            raise ValueError("NIP must contain exactly 10 digits")

        weights = [6, 5, 7, 2, 3, 4, 5, 6, 7]
        checksum = sum(int(value[i]) * weights[i] for i in range(9)) % 11

        if checksum == 10:
            # According to Polish rules, modulo 11 == 10 is invalid NIP
            raise ValueError("Invalid NIP checksum")

        if checksum != int(value[9]):
            raise ValueError("Invalid NIP checksum")

        return value


class CompanyResponse(CompanyBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
