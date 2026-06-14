from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    bio: Optional[str] = None 
    email_notifications: Optional[bool] = True 

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=72)

class UserResponse(UserBase):
    id: int
    created_at: datetime
    profile_image: Optional[str] = None

    class Config:
        from_attributes = True

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    email_notifications: Optional[bool] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


# drawings
class DrawingBase(BaseModel):
    title: Optional[str] = None 

class DrawingResponse(DrawingBase):
    id: int
    user_id: int
    image_url: str
    created_at: datetime 
    analysis_output: Optional[Any] = None 
    is_favorite: bool

    class Config:
        from_attributes = True

# auth
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str
