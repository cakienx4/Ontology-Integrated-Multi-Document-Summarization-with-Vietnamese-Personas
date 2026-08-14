from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from api.dependencies import app_state
from api.routers import profiles, inferences, communities, summarize

@asynccontextmanager
async def lifespan(app: FastAPI):
    app_state.load()
    yield

app = FastAPI(title="Personas API", lifespan=lifespan)
app.include_router(summarize.router, prefix="/summarize", tags=["summarize"])
app.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
app.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
app.include_router(inferences.router, prefix="/inferences", tags=["inferences"])
app.include_router(communities.router, prefix="/communities", tags=["communities"])
app.include_router(summarize.router, prefix="/summarize", tags=["summarize"])