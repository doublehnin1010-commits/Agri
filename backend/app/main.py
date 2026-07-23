from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.chroma import connect_chroma
from app.db.mongodb import close_mongodb, connect_mongodb
from app.middleware.rbac import RBACMiddleware
from app.routers import auth, chat, favorites, history, import_excel, proverbs, quiz, reindex, speech, transcribe
from app.services.favorite_service import configure_favorites
from app.services.embedding_service import configure_embeddings
from app.services.llm_service import configure_llm
from app.services.retriever_service import configure_retriever


app = FastAPI(title=settings.app_name)

app.add_middleware(RBACMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_v1_prefix, tags=["auth"])
app.include_router(import_excel.router, prefix=settings.api_v1_prefix, tags=["dataset"])
app.include_router(proverbs.router, prefix=settings.api_v1_prefix, tags=["proverbs"])
app.include_router(chat.router, prefix=settings.api_v1_prefix, tags=["chat"])
app.include_router(quiz.router, prefix=settings.api_v1_prefix, tags=["quiz"])
app.include_router(favorites.router, prefix=settings.api_v1_prefix, tags=["favorites"])
app.include_router(speech.router, prefix=settings.api_v1_prefix, tags=["voice"])
app.include_router(transcribe.router, prefix=settings.api_v1_prefix, tags=["voice"])
app.include_router(history.router, prefix=settings.api_v1_prefix, tags=["history"])
app.include_router(reindex.router, prefix=settings.api_v1_prefix, tags=["dataset"])


@app.on_event("startup")
async def on_startup():
    connect_mongodb()
    configure_embeddings()
    connect_chroma()
    configure_llm()
    configure_retriever()
    await configure_favorites()


@app.on_event("shutdown")
async def on_shutdown():
    close_mongodb()


@app.get("/health")
async def health():
    return {"ok": True, "app": settings.app_name, "env": settings.environment}
