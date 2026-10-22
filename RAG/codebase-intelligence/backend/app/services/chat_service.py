from typing import List
import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.rag.citations import extract_and_validate_citations
from app.rag.llm_adapter import get_llm_provider
from app.rag.prompts import SYSTEM_PROMPT, build_user_prompt
from app.repositories.chat_repo import ChatRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    CitationResponse,
    ConversationDetailResponse,
    ConversationResponse,
    MessageResponse,
)
from app.schemas.search import SearchRequest
from app.services.retrieval_service import RetrievalService


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.chat_repo = ChatRepository(db)
        self.retrieval_service = RetrievalService(db)
        self.llm = get_llm_provider()

    def answer_question(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        req: ChatRequest,
    ) -> ChatResponse:
        # Validate project ownership
        project = self.project_repo.get_by_id_and_user(project_id, user_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or you do not have permission to access it.",
            )

        if project.status != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project is not ready for querying (status: '{project.status}').",
            )

        # Get or create conversation
        if req.conversation_id:
            conversation = self.chat_repo.get_conversation(req.conversation_id, user_id)
            if not conversation or conversation.project_id != project_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found or unauthorized.",
                )
        else:
            title = req.message[:50].strip() + ("..." if len(req.message) > 50 else "")
            conversation = self.chat_repo.create_conversation(
                project_id=project_id, user_id=user_id, title=title
            )

        # Record user message
        self.chat_repo.add_message(
            conversation_id=conversation.id, role="user", content=req.message
        )

        # Retrieve relevant code context
        search_req = SearchRequest(
            query=req.message,
            top_k=req.top_k,
            use_reranker=req.use_reranker,
        )
        search_res = self.retrieval_service.search(project_id, user_id, search_req)
        retrieved_chunks = search_res.results

        # Build grounded prompt
        user_prompt = build_user_prompt(
            question=req.message, context_chunks=retrieved_chunks
        )

        # LLM generation
        llm_answer = self.llm.generate(SYSTEM_PROMPT, user_prompt)

        # Extract and strictly validate citations
        citations = extract_and_validate_citations(llm_answer, retrieved_chunks)

        # Record assistant message
        assistant_msg = self.chat_repo.add_message(
            conversation_id=conversation.id, role="assistant", content=llm_answer
        )

        # Store citations in database
        saved_citations: List[CitationResponse] = []
        for c in citations:
            saved = self.chat_repo.add_citation(
                message_id=assistant_msg.id,
                chunk_id=c.chunk_id,
                file_path=c.file_path,
                start_line=c.start_line,
                end_line=c.end_line,
                snippet=c.snippet,
            )
            saved_citations.append(CitationResponse.model_validate(saved))

        msg_response = MessageResponse(
            id=assistant_msg.id,
            conversation_id=conversation.id,
            role="assistant",
            content=llm_answer,
            citations=saved_citations,
            created_at=assistant_msg.created_at,
        )

        return ChatResponse(
            conversation_id=conversation.id,
            message=msg_response,
        )

    def list_conversations(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> List[ConversationResponse]:
        convs = self.chat_repo.list_conversations(project_id, user_id)
        results = []
        for c in convs:
            results.append(
                ConversationResponse(
                    id=c.id,
                    project_id=c.project_id,
                    title=c.title,
                    created_at=c.created_at,
                    message_count=len(c.messages),
                )
            )
        return results

    def get_conversation_detail(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> ConversationDetailResponse:
        conversation = self.chat_repo.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or unauthorized.",
            )

        messages = self.chat_repo.get_messages(conversation_id)
        msg_responses = []
        for m in messages:
            msg_responses.append(
                MessageResponse(
                    id=m.id,
                    conversation_id=m.conversation_id,
                    role=m.role,
                    content=m.content,
                    citations=[CitationResponse.model_validate(c) for c in m.citations],
                    created_at=m.created_at,
                )
            )

        return ConversationDetailResponse(
            id=conversation.id,
            project_id=conversation.project_id,
            title=conversation.title,
            created_at=conversation.created_at,
            message_count=len(msg_responses),
            messages=msg_responses,
        )
