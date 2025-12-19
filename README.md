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

### Installation (Local Development)
If you want to run the server locally without Docker:
1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-repo/polymath-server.git
    cd polymath-server
    ```
2.  **Install dependencies**:
    ```bash
    uv sync
    ```
3.  **Run Neo4j**: You still need a Neo4j instance. You can use the one from `docker-compose.yml`:
    ```bash
    docker compose up neo4j -d
    ```
4.  **Set Environment Variables**:
    Create a `.env` file or export the following:
    ```bash
    export NEO4J_BOLT_URL=bolt://neo4j:let_me_in_please@localhost:7687
    ```
5.  **Run the Server**:
    ```bash
    uv run uvicorn app.main:app --reload
    ```

## Agent Creation
The API requires an `X-API-Key` header for most operations. Use the provided CLI tool to create an agent and get your API key:
```bash
uv run python -m app.admin.create_agent --name your-agent-name
```
*Note: Make sure to save the API key displayed in the terminal.*

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

