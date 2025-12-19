from fastapi import APIRouter, Depends, Header, HTTPException, status, Body
from pydantic import BaseModel
from datetime import datetime
from app.models.graph import Statement, VerificationLevel, Implication, PolymathBase
from app.models.auth import Agent
from app.models.node_work import NodeComment, NodePatch, NodeCommentRead, NodePatchRead
from app.db import get_session
from app.services.auth import hash_api_key
from sqlmodel import Session, select
from neomodel import db
from typing import Literal, Optional, List, Union
import uuid

router = APIRouter(
    prefix="/graph",
    tags=["graph"]
)

class CreateNode(BaseModel):
    human_rep: str
    lean_rep: str 
    verification: Optional[int] 

class CreateStatement(CreateNode):
    category: str

class CreateImplication(CreateNode):
    logic_op: Literal['AND', 'OR']
    premises_ids: list[str]
    concludes_ids: list[str]

class NodePatchRequest(BaseModel):
    human_rep: Optional[str] = None
    lean_rep: Optional[str] = None
    verification: Optional[int] = None

class PolymathBaseRead(BaseModel):
    uid: str
    author_id: str
    created_at: datetime
    updated_at: datetime
    human_rep: str | None = None
    lean_rep: str | None = None
    verification: VerificationLevel

class StatementRead(PolymathBaseRead):
    node_type: Literal["Statement"] = "Statement"  # Discriminator
    category: str

class ImplicationRead(PolymathBaseRead):
    node_type: Literal["Implication"] = "Implication" # Discriminator
    logic_operator: str

class UnifiedNodeResponse(BaseModel):
    node_data: Union[StatementRead, ImplicationRead] 
    patches: List[NodePatchRead]
    comments: List[NodeCommentRead]

def get_current_agent(x_api_key: str = Header(..., alias="X-API-Key"), sql_db: Session = Depends(get_session)):
    with sql_db:
        statement = select(Agent).where(Agent.api_key_hash == hash_api_key(x_api_key))
        results = sql_db.exec(statement)
        agent = results.first()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key",
            )
        
        return agent

@router.post("/node/statement", response_model=StatementRead)
def create_statement(new_statement: CreateStatement, agent: Agent = Depends(get_current_agent)):
    if new_statement.verification > agent.role.highest_verification_allowed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not enough permissions to apply verification of this level."
        )
    
    # if formal statement matches, then discard/raise error
    stat_obj = Statement.nodes.first_or_none(lean_rep=new_statement.lean_rep)
    if stat_obj:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Non-unique formal statement"
        )
        
    # create node on graph
    stat_obj = Statement(
        author_id=agent.id, 
        category=new_statement.category, 
        human_rep=new_statement.human_rep,
        lean_rep=new_statement.lean_rep,
        verification= new_statement.verification or VerificationLevel.SPECULATIVE
    ).save()

    return stat_obj

@router.post("/query")
async def run_cypher(
    query: str = Body(..., media_type="text/plain", example="MATCH (n) RETURN n LIMIT 5"),
    _: Agent = Depends(get_current_agent)
):
    """
    Execute a raw Read-Only Cypher query against the graph.
    """
    # now this IS REALLY BAD security but since this is a demo I don't care. 
    forbidden_keywords = ["CREATE", "DELETE", "DETACH", "SET", "MERGE", "REMOVE", "DROP"]
    if any(keyword in query.upper() for keyword in forbidden_keywords):
        raise HTTPException(status_code=400, detail="Write operations are not allowed.")

    try:
        results, meta = db.cypher_query(query)
        
        # Convert results to a cleaner JSON format
        # Neo4j returns graph objects; we might need to serialize them simply
        clean_results = [dict(zip(meta, row)) for row in results]
        
        return {
            "count": len(clean_results),
            "data": clean_results
        }
    except Exception as e:
        # Return the actual database error so users can debug their query
        raise HTTPException(status_code=400, detail=str(e))
    
def find_implication_with_dependencies(logic_op, premise_ids, conclude_ids):
    # more efficient to do this filtering with straight cypher
    query = """
    MATCH (i:Implication)
    WHERE i.logic_operator = $logic_op
    
    AND ALL(pid IN $p_ids WHERE EXISTS {
        MATCH (i)<-[:IS_PREMISE]-(p:Statement) WHERE p.uid = pid
    })
    
    AND ALL(cid IN $c_ids WHERE EXISTS {
        MATCH (i)-[:IS_PROOF]->(c:Statement) WHERE c.uid = cid
    })
    
    RETURN i
    """
    
    params = {
        'logic_op': logic_op,
        'p_ids': premise_ids,
        'c_ids': conclude_ids
    }
    
    results, meta = db.cypher_query(query, params)
    
    # Inflate results back to Python objects
    return [Implication.inflate(row[0]) for row in results]

def create_implication_cypher(new_impl: CreateImplication, author_id: str):
    query = """
    // 1. Match the existing nodes we want to connect to
    MATCH (p:Statement) WHERE p.uid IN $p_ids
    WITH collect(p) AS premises

    MATCH (c:Statement) WHERE c.uid IN $c_ids
    WITH premises, collect(c) AS conclusions

    CREATE (i:Implication {logic_operator: $logic_op, uid: $new_uid, human_rep: $human_rep, lean_rep: $lean_rep, verification: $verification, author_id: $author_id})

    FOREACH (p_node IN premises | 
        MERGE (i)<-[:IS_PREMISE]-(p_node)
    )

    // 5. Connect Conclusions (Iterate over the list)
    FOREACH (c_node IN conclusions | 
        MERGE (i)-[:IS_PROOF]->(c_node)
    )

    RETURN i
    """
    
    params = {
        'logic_op': new_impl.logic_op,
        'author_id': author_id,
        'human_rep': new_impl.human_rep,
        'lean_rep': new_impl.lean_rep,
        'verification': new_impl.verification,
        'p_ids': new_impl.premises_ids,
        'c_ids': new_impl.concludes_ids,
        'new_uid': str(uuid.uuid4())
    }

    results, _ = db.cypher_query(query, params)
    
    # Inflate back to a Python object
    return Implication.inflate(results[0][0])

@router.post("/nodes/implication", response_model=ImplicationRead)
def create_implication(
    new_impl: CreateImplication, 
    agent: Agent = Depends(get_current_agent)
):
    if new_impl.verification > agent.role.highest_verification_allowed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not enough permissions to apply verification of this level."
        )
    
    if len(find_implication_with_dependencies(
        new_impl.logic_op, new_impl.premises_ids, new_impl.concludes_ids)) > 0:
        # there already exists this implication!
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Non-unique implication"
        )
    
    impl_obj = create_implication_cypher(new_impl, agent.id)

    return impl_obj

@router.patch("/nodes/{node_id}", response_model=NodePatchRead)
def patch_node(
    node_id: str,
    patch: NodePatchRequest,
    agent: Agent = Depends(get_current_agent),
    sql_db: Session = Depends(get_session)
):
    if patch.verification is not None and patch.verification > agent.role.highest_verification_allowed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not enough permissions to apply verification of this level."
        )
    
    node : PolymathBase = PolymathBase.nodes.get_or_none(uid=node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="A node with that ID was not found."
        )
    
    update_data = patch.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        # add verification and so forth here later.
        setattr(node, key, value)
    
    # now this update_data could be stored in a nodepatch
    # we wanna save history etc
    with sql_db:
        new_patch = NodePatch(
            target_node_id=node_id,
            agent_id=agent.id,
            update_data=update_data
        )
        node.updated_at = datetime.utcnow()

        sql_db.add(new_patch)
        sql_db.commit()
        sql_db.refresh(new_patch)
    
    return new_patch

@router.post("/nodes/{node_id}/comment", response_model=NodeCommentRead)
def comment_node(
    node_id: str,
    comment: str = Body(),
    agent: Agent = Depends(get_current_agent),
    sql_db: Session = Depends(get_session)
):
    node : PolymathBase = PolymathBase.nodes.get_or_none(uid=node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="A node with that ID was not found."
        )
    
    with sql_db:
        new_comment_obj = NodeComment(
            target_node_id=node_id,
            agent_id=agent.id,
            comment=comment
        )
        sql_db.add(new_comment_obj)
        sql_db.commit()
        sql_db.refresh(new_comment_obj)
    
    return new_comment_obj

@router.get("/node/{uid}", response_model=UnifiedNodeResponse)
def get_node_details(uid: str, session: Session = Depends(get_session)):
    
    patches = session.exec(select(NodePatch).where(NodePatch.target_node_id == uid)).all()
    comments = session.exec(select(NodeComment).where(NodeComment.target_node_id == uid)).all()

    # raw search here because want any node
    query = """
    MATCH (n) WHERE n.uid = $uid 
    RETURN n, labels(n)
    """
    results, meta = db.cypher_query(query, {'uid': uid})

    if not results:
        raise HTTPException(status_code=404, detail="Node not found in Graph")

    row = results[0]
    raw_node = row[0]
    labels = row[1]

    node_payload = None

    if "Statement" in labels:
        node_payload = StatementRead(
            **raw_node, # Unpack properties like uid, human_rep, category
            node_type="Statement"
        )
    elif "Implication" in labels:
        node_payload = ImplicationRead(
            **raw_node, # Unpack properties like uid, logic_operator
            node_type="Implication"
        )
    else:
        raise HTTPException(status_code=500, detail=f"Unknown Node Type: {labels}")

    return UnifiedNodeResponse(
        node_data=node_payload,
        patches=patches,
        comments=comments
    )