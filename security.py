import hashlib, secrets, os
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import User, SessionToken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)
TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "12"))

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def create_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(SessionToken(token_hash=hash_token(token), user_id=user.id,
                        expires_at=datetime.now(timezone.utc) + timedelta(hours=TTL_HOURS)))
    db.commit()
    return token

def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    if not creds:
        raise HTTPException(status_code=401, detail="Authentication required")
    row = db.query(SessionToken).filter_by(token_hash=hash_token(creds.credentials), revoked=False).first()
    if not row or row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    user = db.query(User).filter_by(id=row.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")
    return user

def require_roles(*roles):
    def dependency(user: User = Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return dependency
