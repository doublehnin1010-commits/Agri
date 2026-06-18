from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.chroma import connect_chroma
from app.db.mongodb import close_mongodb, connect_mongodb
from app.middleware.rbac import RBACMiddleware
from app.routers import auth, chat, history, import_excel, proverbs, reindex
from app.services.ollama import configure_ollama


app = FastAPI(title=settings.app_name)

app.add_middleware(RBACMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, tags=["auth"])
app.include_router(import_excel.router, tags=["dataset"])
app.include_router(proverbs.router, tags=["proverbs"])
app.include_router(chat.router, tags=["chat"])
app.include_router(history.router, tags=["history"])
app.include_router(reindex.router, tags=["dataset"])


@app.on_event("startup")
async def on_startup():
    connect_mongodb()
    connect_chroma()
    configure_ollama()


    # Ensure chroma is connected and available for reindex endpoint
    # (connect_chroma already sets the collection on startup)


@app.on_event("shutdown")
async def on_shutdown():
    close_mongodb()


@app.get("/health")
async def health():
    return {"ok": True, "app": settings.app_name, "env": settings.environment}

