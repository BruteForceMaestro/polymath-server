
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

app.include_router(graph.router)