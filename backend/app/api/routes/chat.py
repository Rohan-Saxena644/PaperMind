from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from app.db.session import get_db
from app.models.models import User, Chat, Message
from app.schemas.schemas import ChatCreate, ChatOut, ChatAskRequest, MessageOut, MessageSource
from app.api.deps import get_current_user
from app.services.ai.gemini import AIRateLimitError, get_query_embedding, answer_question
from app.services.ai.vector_store import search_chunks

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
def create_chat(
    payload: ChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = Chat(user_id=current_user.id, title=payload.title)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return ChatOut.model_validate(chat)


@router.get("/", response_model=list[ChatOut])
def list_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chats = (
        db.query(Chat)
        .filter(Chat.user_id == current_user.id)
        .order_by(Chat.created_at.desc())
        .all()
    )
    return [ChatOut.model_validate(c) for c in chats]


@router.get("/{chat_id}", response_model=ChatOut)
def get_chat(
    chat_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = db.query(Chat).filter(
        Chat.id == chat_id, Chat.user_id == current_user.id
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return ChatOut.model_validate(chat)


@router.post("/{chat_id}/ask", response_model=MessageOut)
def ask_question(
    chat_id: uuid.UUID,
    payload: ChatAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = db.query(Chat).filter(
        Chat.id == chat_id, Chat.user_id == current_user.id
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Save user message
    user_msg = Message(chat_id=chat.id, role="user", content=payload.question)
    db.add(user_msg)
    db.commit()

    try:
        # 1. Embed the question
        query_embedding = get_query_embedding(payload.question)

        # 2. Retrieve relevant chunks from vector store
        paper_ids = [str(pid) for pid in payload.paper_ids] if payload.paper_ids else None
        chunks = search_chunks(
            query_embedding=query_embedding,
            user_id=str(current_user.id),
            paper_ids=paper_ids,
            top_k=8,
        )

        if not chunks:
            answer = "I couldn't find relevant information in your papers. Please upload some papers first."
            sources = []
        else:
            # 3. Generate answer with Gemini
            answer = answer_question(payload.question, chunks)
            sources = [
                {
                    "paper_id": c["paper_id"],
                    "paper_title": c["paper_title"],
                    "chunk_content": c["content"][:300],
                    "score": c["score"],
                }
                for c in chunks[:3]  # top 3 sources in response
            ]
    except AIRateLimitError as exc:
        db.delete(user_msg)
        db.commit()
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    # 4. Save assistant message
    assistant_msg = Message(
        chat_id=chat.id,
        role="assistant",
        content=answer,
        sources=sources,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return MessageOut.model_validate(assistant_msg)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = db.query(Chat).filter(
        Chat.id == chat_id, Chat.user_id == current_user.id
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    db.delete(chat)
    db.commit()
