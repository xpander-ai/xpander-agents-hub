from fastapi import FastAPI
from .database import engine, Base
from .api.v1.api import api_router
from .core.config import settings

# Import your models to ensure they're registered with the Base
from . import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}