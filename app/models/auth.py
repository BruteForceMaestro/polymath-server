from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from app.models.graph import VerificationLevel
from typing import List

if TYPE_CHECKING:
    from app.models.node_work import NodePatch, NodeComment

class Role(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    name: str = Field(index=True, unique=True) 
    
    # This integer determines the ceiling of what this role can commit
    highest_verification_allowed: int = Field(
        default=VerificationLevel.SPECULATIVE,
        description="The maximum VerificationLevel int value this role is allowed to assign."
    )

    agents: List["Agent"] = Relationship(back_populates="role")


class Agent(SQLModel, table=True):
    
    id: Optional[int] = Field(default=None, primary_key=True)

    name: str = Field(index=True)

    api_key_hash: str = Field(index=True, unique=True)

    role_id: Optional[int] = Field(default=None, foreign_key="role.id")
    
    role: Optional[Role] = Relationship(back_populates="agents")

    node_patches: List["NodePatch"] = Relationship(back_populates="agent")

    node_comments: List["NodeComment"] = Relationship(back_populates="agent")
