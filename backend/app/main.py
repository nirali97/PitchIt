from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .main_state import engine, settings
from .db import Base
from . import models  # register tables
from .api.routes import router

app=FastAPI(title="PitchIt API",version="0.1.0",description="An adaptive consulting reasoning and practice platform")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_list,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(router)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get('/')
def root(): return {"name":"PitchIt API","status":"ok","docs":"/docs"}

@app.get('/health')
def health(): return {"status":"healthy"}
