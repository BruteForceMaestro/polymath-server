#!/bin/bash
# Check if the API key is provided
if [ -z "$1" ]; then
    echo "Error: Missing API key."
    echo "Usage: ./query.sh <API_KEY> [\"<CYPHER_QUERY>\"]"
    exit 1
fi

API_KEY=$1
# Use $2 if provided, otherwise default to a basic count query
QUERY=${2:-"MATCH (n) RETURN count(n) AS node_count"}

echo "Executing query: $QUERY"

curl -s -X POST "http://localhost:8000/graph/query" \
     -H "Content-Type: text/plain" \
     -H "X-API-Key: $API_KEY" \
     --data-binary "$QUERY"