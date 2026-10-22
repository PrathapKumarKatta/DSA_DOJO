from typing import List, Optional
import uuid
from sqlalchemy.orm import Session, joinedload
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.citation import MessageCitation


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_conversation(
        self, project_id: uuid.UUID, user_id: uuid.UUID, title: str = "New Chat"
    ) -> Conversation:
        conversation = Conversation(
            project_id=project_id, user_id=user_id, title=title
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_conversation(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Conversation]:
        return (
            self.db.query(Conversation)
            .filter(
                Conversation.id == conversation_id, Conversation.user_id == user_id
            )
            .first()
        )

    def list_conversations(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> List[Conversation]:
        return (
            self.db.query(Conversation)
            .filter(
                Conversation.project_id == project_id, Conversation.user_id == user_id
            )
            .order_by(Conversation.created_at.desc())
            .all()
        )

    def add_message(
        self, conversation_id: uuid.UUID, role: str, content: str
    ) -> Message:
        message = Message(
            conversation_id=conversation_id, role=role, content=content
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def add_citation(
        self,
        message_id: uuid.UUID,
        chunk_id: Optional[uuid.UUID],
        file_path: str,
        start_line: int,
        end_line: int,
        snippet: Optional[str] = None,
    ) -> MessageCitation:
        citation = MessageCitation(
            message_id=message_id,
            chunk_id=chunk_id,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            snippet=snippet,
        )
        self.db.add(citation)
        self.db.commit()
        self.db.refresh(citation)
        return citation

    def get_messages(self, conversation_id: uuid.UUID) -> List[Message]:
        return (
            self.db.query(Message)
            .options(joinedload(Message.citations))
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )
