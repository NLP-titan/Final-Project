from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=32)
    region: Optional[str] = Field(default=None, max_length=128)
    nhis_number: Optional[str] = Field(default=None, max_length=32)
    membership_type: Optional[str] = Field(default=None, max_length=32)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    role: str
    is_active: bool
    phone: Optional[str] = None
    region: Optional[str] = None
    nhis_number: Optional[str] = None
    membership_type: Optional[str] = None
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    phone: Optional[str] = Field(default=None, max_length=32)
    region: Optional[str] = Field(default=None, max_length=128)
    nhis_number: Optional[str] = Field(default=None, max_length=32)
    membership_type: Optional[str] = Field(default=None, max_length=32)


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    role: Optional[str] = Field(default=None, pattern="^(admin|user)$")
    is_active: Optional[bool] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
