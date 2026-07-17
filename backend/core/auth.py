import os
import bcrypt
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from pathlib import Path

# Load .env locally if present; on Railway env vars are set in dashboard
env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

SECRET_KEY = os.getenv("JWT_SECRET", "med-ai-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

bearer_scheme = HTTPBearer()


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# All users: reviewers + all doctors from the doctor portal
USERS = {
    "admin": {
        "username": "admin",
        "hashed_password": _hash("admin123"),
        "role": "admin",
        "name": "Administrator",
    },
    "reviewer": {
        "username": "reviewer",
        "hashed_password": _hash("review2025"),
        "role": "reviewer",
        "name": "Reviewer",
    },
    "dr.smith": {
        "username": "dr.smith",
        "hashed_password": _hash("medai2025"),
        "role": "doctor",
        "name": "Dr. John Smith",
    },
    "dr.jones": {
        "username": "dr.jones",
        "hashed_password": _hash("jones2025"),
        "role": "doctor",
        "name": "Dr. Sarah Jones",
    },
    "dr.patel": {
        "username": "dr.patel",
        "hashed_password": _hash("patel2025"),
        "role": "doctor",
        "name": "Dr. Raj Patel",
    },
    "dr.chen": {
        "username": "dr.chen",
        "hashed_password": _hash("chen2025"),
        "role": "doctor",
        "name": "Dr. Linda Chen",
    },
    "dr.williams": {
        "username": "dr.williams",
        "hashed_password": _hash("williams2025"),
        "role": "doctor",
        "name": "Dr. Marcus Williams",
    },
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username or username not in USERS:
            raise HTTPException(status_code=401, detail="Invalid token")
        return USERS[username]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_role(role: str):
    def checker(user=Depends(get_current_user)):
        if user["role"] != role and user["role"] != "admin":
            raise HTTPException(status_code=403, detail=f"Requires {role} role")
        return user
    return checker
