from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from app.routers import graph
from contextlib import asynccontextmanager
from neomodel import config
from app.db import init_dbs

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_dbs()
    yield


app = FastAPI(lifespan=lifespan)

# Define the origins that are allowed to make requests to your API
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # Or use ["*"] for total anarchy (local dev only)
    allow_credentials=True,
    allow_methods=["*"],              # Allows POST, GET, OPTIONS, etc.
    allow_headers=["*"],              # Allows Content-Type, Authorization, etc.
)

app.include_router(graph.router)
