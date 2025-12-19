# neomodel graph nodes

from neomodel import (
    StructuredNode, 
    StringProperty, 
    JSONProperty, 
    DateTimeProperty, 
    RelationshipTo, 
    RelationshipFrom,
    UniqueIdProperty,
    IntegerProperty
)
from datetime import datetime
from enum import IntEnum

class VerificationLevel(IntEnum):
    REJECTED = 0          # Proven false
    SPECULATIVE = 1       # LLM/Human guess
    NUMERICAL = 2         # Verified in Python but not Lean
    FORMAL_SKETCH = 3     # Lean code exists, assumes 'sorry'
    VERIFIED = 4          # Compiled successfully

VERIFICATION_CHOICES = [(status.value, status.name) for status in VerificationLevel]

class PolymathBase(StructuredNode):
    """
    Abstract base class for all nodes in the protocol.
    """
    __abstract_node__ = True

    # Unique ID 
    uid = UniqueIdProperty()
    
    # Metadata
    created_at = DateTimeProperty(default_datetime=datetime.utcnow)
    updated_at = DateTimeProperty(default_datetime=datetime.utcnow)
    
    # Who created this node (Agent ID)
    author_id = StringProperty(required=True)
    
    # 2 dialects: human or lean
    human_rep = StringProperty()
    lean_rep = StringProperty()
    
    # Verification Metadata
    verification = IntegerProperty(
        choices=VERIFICATION_CHOICES, 
        default=VerificationLevel.SPECULATIVE
    )


class Statement(PolymathBase):
    """
    Represents a Theorem, Axiom, Lemma, or Definition.
    The 'Dot' in the graph.
    """
    # theorem, lemma, axiom, or definition
    category = StringProperty(default="CONJECTURE")
    
    proven_by = RelationshipFrom('Implication', 'IS_PROOF')
    
    supports = RelationshipTo('Implication', 'IS_PREMISE')

class Implication(PolymathBase):
    """
    Represents the logical step or proof.
    The 'Hyperedge' in the graph (Reified as a Node).
    """
    # and, or
    logic_operator = StringProperty(default="AND")
    
    premises = RelationshipFrom('Statement', 'IS_PREMISE')
    
    concludes = RelationshipTo('Statement', 'IS_PROOF')
