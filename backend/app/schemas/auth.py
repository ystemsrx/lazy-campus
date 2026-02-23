from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    account: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    captcha_token: str | None = None
    session_id: str | None = None


class RegisterRequest(BaseModel):
    account: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=100)
    captcha_token: str = Field(min_length=8, max_length=64)
    session_id: str = Field(min_length=8, max_length=64)


class TokenData(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class LoginResponse(BaseModel):
    token: TokenData
    role: str
    profile_completed: bool
    user_id: int | None = None
    display_name: str


class RegisterResponse(BaseModel):
    user_id: int
    account: str


class RegistrationStatusResponse(BaseModel):
    registration_enabled: bool


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class ThirdPartyRequest(BaseModel):
    account: str
    password: str


class ThirdPartyUserData(BaseModel):
    name: str
    accountId: str
    avatarUrl: str | None = ''
    idNumber: str | None = None


class ThirdPartyResponse(BaseModel):
    success: bool
    code: int
    msg: str | None = None
    data: ThirdPartyUserData | None = None
