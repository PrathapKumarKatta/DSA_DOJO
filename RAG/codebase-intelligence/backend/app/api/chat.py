import uuid
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
    ConversationResponse,
)
from app.schemas.search import SearchRequest, SearchResponse
from app.services.chat_service import ChatService
from app.services.retrieval_service import RetrievalService

router = APIRouter(tags=["chat"])


@router.post(
    "/projects/{id}/search",
    response_model=SearchResponse,
    summary="Search codebase using hybrid retrieval (vector + keyword) and optional reranking",
)
def search_codebase(
    id: uuid.UUID,
    req: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchResponse:
    retrieval_service = RetrievalService(db)
    return retrieval_service.search(project_id=id, user_id=current_user.id, req=req)


@router.post(
    "/projects/{id}/chat",
    response_model=ChatResponse,
    summary="Ask questions about the codebase with grounded citations",
)
def chat_with_codebase(
    id: uuid.UUID,
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    chat_service = ChatService(db)
    return chat_service.answer_question(project_id=id, user_id=current_user.id, req=req)


@router.get(
    "/projects/{id}/conversations",
    response_model=List[ConversationResponse],
    summary="List all conversations for a project",
)
def list_project_conversations(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ConversationResponse]:
    chat_service = ChatService(db)
    return chat_service.list_conversations(project_id=id, user_id=current_user.id)


@router.get(
    "/conversations/{id}/messages",
    response_model=ConversationDetailResponse,
    summary="Get full conversation history and message citations",
)
def get_conversation_history(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetailResponse:
    chat_service = ChatService(db)
    return chat_service.get_conversation_detail(conversation_id=id, user_id=current_user.id)
