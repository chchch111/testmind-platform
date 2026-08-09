from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=100)


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=6, max_length=100)
    real_name: str | None = Field(default=None, max_length=50)
    role_code: str = Field(default="tester", max_length=30)
    email: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)


class UserPasswordReset(BaseModel):
    new_password: str = Field(min_length=6, max_length=100)


class UserInfoOut(BaseModel):
    user_id: int
    username: str
    real_name: str | None
    role_code: str

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: int
    user: UserInfoOut
