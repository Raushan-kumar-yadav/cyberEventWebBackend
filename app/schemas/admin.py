from pydantic import BaseModel, Field


# admin login request
class AdminLogin(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    passcode: str = Field(min_length=1, max_length=128)


# admin session
class AdminSession(BaseModel):
    admin_id: int
    admin_name: str
