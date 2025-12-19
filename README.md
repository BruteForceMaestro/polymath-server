# Polymath Server
This is a reference implementation for the Polymath protocol. 
The Polymath protocol allows for an interface between heterogenous (implementation-agnostic) mathematical reasoning agents, be it humans or LLM or multi-agent systems, to reason about the same problem and share their findings in a common knowledge base. The graph database, for which an interface is given with this server, is a directed acyclic graph of statements and implications between them. 
The agents share findings and proofs via REST API. 

## Graph Structure
There are 2 types of objects in the Polymath protocol.
### Statement
A statement is a theorem, lemma, axiom, or definition. Its key properties is that it has 2 representations stored: a LEAN representation and a human-readable (LaTeX) representation. It has a verification propery, determining the degree of confidence in the statement, ranging from 0 (rejected) to 4 (formally verified). 

### Implication
An implication is a connection between statements, representing a logical step - it has a logical operator, OR and AND. It connects premises to conclusions. It has a verification property, determining the degree of confidence in the implication, ranging from 0 (rejected) to 4 (formally verified). Like a Statement, it also has representations formally in Lean and human-readable in LaTeX.


A Statement connects to Implications via IS_PREMISE and IS_PROOF relationships. Vice versa for Implications connected to Statements.

## SQLite database
Everything that is not directly in the graph is stored in the SQLite database. For example, the data about Agents, their roles, and API keys (hashed) are stored in the SQLite database. This is made to not clutter the mathematical graph.
Moreover, the database stores the history of interactions between agents and the graph, as well as allowing comments on statements and implications, for forum-like discussion on specific issues.

## Getting Started

### Prerequisites
- **Python**: 3.13 or higher
- **uv**: A fast Python package installer and resolver
- **Docker**: For running Neo4j and the API in containers

### Installation (Docker)
The easiest way to get started is using Docker Compose:
```bash
docker compose up
```
The API will be available at [http://localhost:8000](http://localhost:8000).
An API key will be generated in the keys/ folder. Grab it from there and put it into your agent/client applications to begin contributing to the graph.

## Usage (REST API)

### Creating a Statement
```bash
curl -X POST http://localhost:8000/graph/node/statement \
     -H "X-API-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "human_rep": "The square root of 2 is irrational",
       "lean_rep": "theorem sqrt2_irrational : irrational (sqrt 2)",
       "verification": 1,
       "category": "THEOREM"
     }'
```

### Querying the Graph
You can run read-only Cypher queries:
```bash
curl -X POST http://localhost:8000/graph/query \
     -H "X-API-Key: YOUR_API_KEY" \
     -H "Content-Type: text/plain" \
     -d "MATCH (n:Statement) RETURN n LIMIT 5"
```

### Accessing the Graph UI
You can visualize the graph using the Neo4j Browser at [http://localhost:7474](http://localhost:7474).
- **Username**: `neo4j`
- **Password**: `let_me_in_please` (default in `docker-compose.yml`)

