from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    company_name: str
    company_slug: str
    vertical: str | None = None
    full_name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"