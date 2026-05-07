from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from pramaan.db.session import get_db
from pramaan.db.models import Officer, Bidder

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str
    password: str
    role: str

class LoginResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """
    Authenticate a user.
    Accept ANY credentials as requested by the user for testing the inner application.
    Fully mocked to bypass DB connection errors.
    """
    if request.role == "admin":
        return LoginResponse(
            id="mock-admin-id",
            email=request.email,
            name="Mock Admin",
            role="admin"
        )
            
    elif request.role == "bidder":
        return LoginResponse(
            id="mock-bidder-id",
            email=request.email,
            name="Mock Bidder",
            role="bidder"
        )
            
    return LoginResponse(
        id="mock-user-id",
        email=request.email,
        name="Mock User",
        role=request.role
    )
