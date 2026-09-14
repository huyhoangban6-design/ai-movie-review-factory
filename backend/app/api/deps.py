from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        _raise_unauthorized()
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        _raise_unauthorized()
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        _raise_unauthorized()
    return user


def _raise_unauthorized() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_idempotency_key(key: str | None = Header(default=None, alias="Idempotency-Key")) -> str | None:
    if key is None:
        return None
    key = key.strip()
    if len(key) < 8 or len(key) > 255:
        raise HTTPException(status_code=400, detail="Idempotency-Key must be 8..255 characters")
    return key