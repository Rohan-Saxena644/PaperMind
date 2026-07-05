from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from app.api.deps import get_current_user, get_or_create_default_workspace
from app.db.session import get_db
from app.models.models import Chat, FlashcardReview, Paper, User, Workspace
from app.schemas.schemas import WorkspaceCreate, WorkspaceOut, WorkspaceUpdate

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("/", response_model=list[WorkspaceOut])
def list_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_or_create_default_workspace(db, current_user)
    workspaces = (
        db.query(Workspace)
        .filter(Workspace.user_id == current_user.id)
        .order_by(Workspace.is_default.desc(), Workspace.created_at.asc())
        .all()
    )
    return [WorkspaceOut.model_validate(workspace) for workspace in workspaces]


@router.post("/", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = Workspace(
        user_id=current_user.id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return WorkspaceOut.model_validate(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.user_id == current_user.id)
        .first()
    )
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if payload.name is not None:
        workspace.name = payload.name.strip()
    if payload.description is not None:
        workspace.description = payload.description.strip() or None

    db.commit()
    db.refresh(workspace)
    return WorkspaceOut.model_validate(workspace)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.user_id == current_user.id)
        .first()
    )
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if workspace.is_default:
        raise HTTPException(status_code=400, detail="Default workspace cannot be deleted")

    has_content = (
        db.query(Paper.id).filter(Paper.workspace_id == workspace.id).first()
        or db.query(Chat.id).filter(Chat.workspace_id == workspace.id).first()
        or db.query(FlashcardReview.id).filter(FlashcardReview.workspace_id == workspace.id).first()
    )
    if has_content:
        raise HTTPException(status_code=400, detail="Move or delete workspace content first")

    db.delete(workspace)
    db.commit()
