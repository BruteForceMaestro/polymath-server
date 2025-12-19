from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from app.models.graph import VerificationLevel


# ------------------------
# Helpers / fakes
# ------------------------

class FakeStatementObj:
    def __init__(
        self,
        *,
        uid: str = "stmt-uid",
        author_id: str = "1",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        human_rep: str | None = "H",
        lean_rep: str | None = "L",
        verification: int = VerificationLevel.SPECULATIVE,
        category: str = "THEOREM",
    ):
        self.uid = uid
        self.author_id = author_id
        self.created_at = created_at or datetime(2020, 1, 1)
        self.updated_at = updated_at or datetime(2020, 1, 2)
        self.human_rep = human_rep
        self.lean_rep = lean_rep
        self.verification = verification
        self.category = category

    def save(self):
        return self


class FakeImplicationObj:
    def __init__(
        self,
        *,
        uid: str = "impl-uid",
        author_id: str = "1",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        human_rep: str | None = "H",
        lean_rep: str | None = "L",
        verification: int = VerificationLevel.SPECULATIVE,
        logic_operator: str = "AND",
    ):
        self.uid = uid
        self.author_id = author_id
        self.created_at = created_at or datetime(2020, 1, 1)
        self.updated_at = updated_at or datetime(2020, 1, 2)
        self.human_rep = human_rep
        self.lean_rep = lean_rep
        self.verification = verification
        self.logic_operator = logic_operator


@pytest.fixture()
def graph_module():
    # Import inside fixture so tests can monkeypatch attributes safely.
    from app.routers import graph as graph_router

    return graph_router


# ------------------------
# POST /graph/node/statement
# ------------------------

def test_create_statement_success(client, graph_module, monkeypatch):
    
    monkeypatch.setattr(graph_module.Statement, "nodes", SimpleNamespace(first_or_none=lambda **kw: None))

    class MockStatement:
        # Mock the static .nodes attribute for the search query
        nodes = SimpleNamespace(first_or_none=lambda **kw: None)

        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def save(self):
            # Return the fake object you defined earlier
            return FakeStatementObj(
                uid="stmt-uid",
                author_id=str(self.kwargs["author_id"]),
                human_rep=self.kwargs.get("human_rep"),
                lean_rep=self.kwargs.get("lean_rep"),
                verification=self.kwargs.get("verification"),
                category=self.kwargs.get("category"),
            )

    monkeypatch.setattr(graph_module, "Statement", MockStatement)

    payload = {
        "category": "THEOREM",
        "human_rep": "hello",
        "lean_rep": "theorem t : True := by trivial",
        "verification": int(VerificationLevel.SPECULATIVE),
    }

    res = client.post("/graph/node/statement", json=payload)
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["uid"] == "stmt-uid"
    assert body["category"] == "THEOREM"
    assert body["human_rep"] == "hello"
    assert body["lean_rep"] == payload["lean_rep"]
    assert body["verification"] == int(VerificationLevel.SPECULATIVE)


def test_create_statement_permission_denied(client, graph_module):
    # override auth dependency to a low-permission agent
    from app.models.auth import Agent, Role

    low_agent = Agent(id=1, name="low", api_key_hash="x", role=Role(name="low", highest_verification_allowed=1))

    client.app.dependency_overrides[graph_module.get_current_agent] = lambda: low_agent

    payload = {
        "category": "THEOREM",
        "human_rep": "hello",
        "lean_rep": "theorem t : True := by trivial",
        "verification": 4,
    }

    res = client.post("/graph/node/statement", json=payload)
    assert res.status_code == 401
    assert res.json()["detail"] == "Not enough permissions to apply verification of this level."


def test_create_statement_non_unique_formal_statement(client, graph_module, monkeypatch):
    monkeypatch.setattr(graph_module.Statement, "nodes", SimpleNamespace(first_or_none=lambda **kw: object()))

    payload = {
        "category": "THEOREM",
        "human_rep": "hello",
        "lean_rep": "duplicate",
        "verification": 1,
    }

    res = client.post("/graph/node/statement", json=payload)
    assert res.status_code == 406
    assert res.json()["detail"] == "Non-unique formal statement"


# ------------------------
# POST /graph/query
# ------------------------

def test_run_cypher_rejects_write_operations(client, graph_module):
    res = client.post("/graph/query", json="CREATE (n)")
    assert res.status_code == 400
    assert res.json()["detail"] == "Write operations are not allowed."


def test_run_cypher_success(client, graph_module, monkeypatch):
    def _cypher_query(query, params=None):
        return [[1, "x"], [2, "y"]], ["id", "val"]

    monkeypatch.setattr(graph_module.db, "cypher_query", _cypher_query)

    res = client.post("/graph/query", json="MATCH (n) RETURN n")
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["count"] == 2
    assert body["data"] == [{"id": 1, "val": "x"}, {"id": 2, "val": "y"}]


def test_run_cypher_returns_db_error(client, graph_module, monkeypatch):
    def _cypher_query(query, params=None):
        raise RuntimeError("bad cypher")

    monkeypatch.setattr(graph_module.db, "cypher_query", _cypher_query)

    res = client.post("/graph/query", json="MATCH (n) RETURN n")
    assert res.status_code == 400
    assert "bad cypher" in res.json()["detail"]


# ------------------------
# POST /graph/nodes/implication
# ------------------------

def test_create_implication_success(client, graph_module, monkeypatch):
    # No duplicates
    monkeypatch.setattr(graph_module, "find_implication_with_dependencies", lambda *_args, **_kw: [])

    fake_impl = FakeImplicationObj(uid="impl-uid", logic_operator="AND")
    monkeypatch.setattr(graph_module, "create_implication_cypher", lambda *_args, **_kw: fake_impl)

    payload = {
        "logic_op": "AND",
        "premises_ids": ["p1"],
        "concludes_ids": ["c1"],
        "human_rep": "step",
        "lean_rep": "by",
        "verification": 1,
    }

    res = client.post("/graph/nodes/implication", json=payload)
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["uid"] == "impl-uid"
    assert body["logic_operator"] == "AND"
    assert body["verification"] == 1


def test_create_implication_duplicate(client, graph_module, monkeypatch):
    monkeypatch.setattr(graph_module, "find_implication_with_dependencies", lambda *_args, **_kw: [object()])

    payload = {
        "logic_op": "AND",
        "premises_ids": ["p1"],
        "concludes_ids": ["c1"],
        "human_rep": "step",
        "lean_rep": "by",
        "verification": 1,
    }

    res = client.post("/graph/nodes/implication", json=payload)
    assert res.status_code == 406
    assert res.json()["detail"] == "Non-unique implication"


# ------------------------
# PATCH /graph/nodes/{node_id}
# ------------------------

def test_patch_node_success_persists_patch(client, graph_module, session, monkeypatch):
    # Fake polymath node in graph
    class _FakeNode:
        def __init__(self):
            self.uid = "n1"
            self.updated_at = datetime(2020, 1, 1)
            self.human_rep = "old"

    fake_node = _FakeNode()

    monkeypatch.setattr(
        graph_module.PolymathBase,
        "nodes",
        SimpleNamespace(get_or_none=lambda **kw: fake_node),
    )

    res = client.patch(
        "/graph/nodes/n1",
        json={"human_rep": "new"},
    )
    print(res.json())
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["target_node_id"] == "n1"
    assert body["update_data"] == {"human_rep": "new"}

    # Ensure it was actually committed to SQL
    from app.models.node_work import NodePatch

    patches = session.exec(graph_module.select(NodePatch).where(NodePatch.target_node_id == "n1")).all()
    assert len(patches) == 1

    assert patches[0].update_data == {"human_rep": "new"}


def test_patch_node_404_when_graph_node_missing(client, graph_module, monkeypatch):
    monkeypatch.setattr(graph_module.PolymathBase, "nodes", SimpleNamespace(get_or_none=lambda **kw: None))

    res = client.patch("/graph/nodes/missing", json={"human_rep": "new"})
    assert res.status_code == 404
    assert res.json()["detail"] == "A node with that ID was not found."


# ------------------------
# POST /graph/nodes/{node_id}/comment
# ------------------------

def test_comment_node_success_persists_comment(client, graph_module, session, monkeypatch):
    monkeypatch.setattr(graph_module.PolymathBase, "nodes", SimpleNamespace(get_or_none=lambda **kw: object()))

    # endpoint expects raw body (JSON string is ok); Body() default media-type is app/json
    res = client.post("/graph/nodes/n1/comment", json="hello")
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["target_node_id"] == "n1"
    assert body["comment"] == "hello"

    from app.models.node_work import NodeComment

    comments = session.exec(graph_module.select(NodeComment).where(NodeComment.target_node_id == "n1")).all()
    assert len(comments) == 1
    assert comments[0].comment == "hello"


def test_comment_node_404_when_graph_node_missing(client, graph_module, monkeypatch):
    monkeypatch.setattr(graph_module.PolymathBase, "nodes", SimpleNamespace(get_or_none=lambda **kw: None))

    res = client.post("/graph/nodes/missing/comment", json="hello")
    assert res.status_code == 404
    assert res.json()["detail"] == "A node with that ID was not found."


# ------------------------
# GET /graph/node/{uid}
# ------------------------

def test_get_node_details_statement_success(client, graph_module, session, monkeypatch):
    # Seed a comment and patch into SQL so endpoint returns them
    from app.models.node_work import NodePatch, NodeComment

    session.add(NodePatch(target_node_id="s1", agent_id="1", update_data={"human_rep": "x"}))
    session.add(NodeComment(target_node_id="s1", agent_id="1", comment="c"))
    session.commit()

    def _cypher_query(query, params=None):
        assert params == {"uid": "s1"}
        raw = {
            "uid": "s1",
            "author_id": "1",
            "created_at": datetime(2020, 1, 1).isoformat(),
            "updated_at": datetime(2020, 1, 2).isoformat(),
            "human_rep": "h",
            "lean_rep": "l",
            "verification": 1,
            "category": "THEOREM",
        }
        return [[raw, ["Statement"]]], ["n", "labels(n)"]

    monkeypatch.setattr(graph_module.db, "cypher_query", _cypher_query)

    res = client.get("/graph/node/s1")
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["node_data"]["node_type"] == "Statement"
    assert body["node_data"]["uid"] == "s1"
    assert body["node_data"]["category"] == "THEOREM"

    assert len(body["patches"]) == 1
    assert len(body["comments"]) == 1


def test_get_node_details_implication_success(client, graph_module, monkeypatch):
    def _cypher_query(query, params=None):
        raw = {
            "uid": "i1",
            "author_id": "1",
            "created_at": datetime(2020, 1, 1).isoformat(),
            "updated_at": datetime(2020, 1, 2).isoformat(),
            "human_rep": "h",
            "lean_rep": "l",
            "verification": 1,
            "logic_operator": "AND",
        }
        return [[raw, ["Implication"]]], ["n", "labels(n)"]

    monkeypatch.setattr(graph_module.db, "cypher_query", _cypher_query)

    res = client.get("/graph/node/i1")
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["node_data"]["node_type"] == "Implication"
    assert body["node_data"]["uid"] == "i1"
    assert body["node_data"]["logic_operator"] == "AND"


def test_get_node_details_404_when_not_in_graph(client, graph_module, monkeypatch):
    monkeypatch.setattr(graph_module.db, "cypher_query", lambda *_args, **_kw: ([], []))

    res = client.get("/graph/node/missing")
    assert res.status_code == 404
    assert res.json()["detail"] == "Node not found in Graph"


def test_get_node_details_500_unknown_node_type(client, graph_module, monkeypatch):
    def _cypher_query(query, params=None):
        return [[{"uid": "x"}, ["Weird"]]], []

    monkeypatch.setattr(graph_module.db, "cypher_query", _cypher_query)

    res = client.get("/graph/node/x")
    assert res.status_code == 500
    assert "Unknown Node Type" in res.json()["detail"]


# ------------------------
# get_current_agent (auth dependency)
# ------------------------

def test_get_current_agent_unauthorized(client_real_auth):
    # No seeded agent, so should be invalid
    res = client_real_auth.post(
        "/graph/query",
        data="MATCH (n) RETURN n",
        headers={"X-API-Key": "nope", "Content-Type": "text/plain"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid API Key"


def test_get_current_agent_authorized(client_real_auth, seeded_agent_in_db, monkeypatch):
    _agent, api_key = seeded_agent_in_db

    # patch cypher_query to avoid real neo4j usage
    from app.routers import graph as graph_module

    monkeypatch.setattr(graph_module.db, "cypher_query", lambda *_args, **_kw: ([], []))

    res = client_real_auth.post(
        "/graph/query",
        data="MATCH (n) RETURN n LIMIT 0",
        headers={"X-API-Key": api_key, "Content-Type": "text/plain"},
    )
    # query returns empty results successfully
    assert res.status_code == 200
    assert res.json() == {"count": 0, "data": []}
