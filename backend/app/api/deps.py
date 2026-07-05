from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import uuid

from app.db.session import get_db
from app.core.security import decode_token
from app.models.models import User, Workspace

bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.get(User, uuid.UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


def get_or_create_default_workspace(db: Session, user: User) -> Workspace:
    workspace = (
        db.query(Workspace)
        .filter(Workspace.user_id == user.id, Workspace.is_default.is_(True))
        .first()
    )
    if workspace:
        return workspace

    workspace = (
        db.query(Workspace)
        .filter(Workspace.user_id == user.id)
        .order_by(Workspace.created_at.asc())
        .first()
    )
    if workspace:
        workspace.is_default = True
        db.commit()
        db.refresh(workspace)
        return workspace

    workspace = Workspace(user_id=user.id, name="My Research", is_default=True)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def get_current_workspace(
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Workspace:
    if x_workspace_id:
        try:
            workspace_id = uuid.UUID(x_workspace_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid workspace id") from exc

        workspace = (
            db.query(Workspace)
            .filter(Workspace.id == workspace_id, Workspace.user_id == current_user.id)
            .first()
        )
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return workspace

    return get_or_create_default_workspace(db, current_user)
