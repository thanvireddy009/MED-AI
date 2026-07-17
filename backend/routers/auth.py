from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from core.auth import USERS, verify_password, create_access_token
from core.audit import log_action

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login", summary="Login and get JWT token")
def login(request: Request, body: LoginRequest):
    user = USERS.get(body.username)
    if not user or not verify_password(body.password, user["hashed_password"]):
        log_action(body.username, "LOGIN_FAILED", ip_address=request.client.host)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": user["username"], "role": user["role"]})
    log_action(user["username"], "LOGIN_SUCCESS", ip_address=request.client.host)

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"]
    }

@router.get("/me", summary="Get current user info")
def me(user: dict = __import__('fastapi').Depends(__import__('core.auth', fromlist=['get_current_user']).get_current_user)):
    return {"username": user["username"], "role": user["role"]}
