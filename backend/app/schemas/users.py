from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.schemas.common import Timestamped


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=128)
    preferred_language: str = Field(default="en", min_length=2, max_length=20)
    location: str | None = Field(default=None, max_length=160)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    preferred_language: str | None = Field(default=None, min_length=2, max_length=20)
    location: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> "UserUpdate":
        for field in ("full_name", "preferred_language"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class UserRead(Timestamped):
    id: str
    email: EmailStr
    full_name: str
    role: str
    preferred_language: str
    location: str | None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class UserRoleUpdate(BaseModel):
    role: str = Field(pattern="^(citizen|admin)$")


class UserProfileUpdate(UserUpdate):
    model_config = ConfigDict(extra="forbid")
