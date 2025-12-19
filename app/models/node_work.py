from sqlmodel import SQLModel, Field, Relationship, Column
from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy.types import JSON

if TYPE_CHECKING:
    from app.models.auth import Agent

class NodeWorkBase(SQLModel):
    """Common fields for any work item (Patch, Comment, etc)"""
    target_node_id: str = Field(index=True)
    agent_id: str = Field(index=True, foreign_key="agent.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class NodePatchBase(NodeWorkBase):
    update_data: Dict[str, Any] = Field(sa_column=Column(JSON))

class NodePatch(NodePatchBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    agent: "Agent" = Relationship(back_populates="node_patches")

class NodePatchRead(NodePatchBase):
    id: int 

class NodeCommentBase(NodeWorkBase):
    comment: str

class NodeComment(NodeCommentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    agent: "Agent" = Relationship(back_populates="node_comments")

class NodeCommentRead(NodeCommentBase):
    id: int