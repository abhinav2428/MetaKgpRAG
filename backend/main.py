"""
backend/main.py
---------------
FastAPI application entry-point.

Run with:
    uvicorn backend.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from backend.config import SECRET_KEY, FRONTEND_URL
from backend.database import engine, Base
from backend.routers import auth_router, conversations_router, chat_router
from backend.rag_service import rag_service

# ── Create all tables on startup (safe to run multiple times) ─────────────────
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GraphMind API",
    description=(
        "GraphRAG-powered conversational AI for MetaKGP / IIT Kharagpur. "
        "Supports multi-turn conversations, user accounts, and conversation history."
    ),
    version="1.0.0",
)

# Session middleware needed by Authlib's OAuth flow
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# CORS – allow the React dev-server and any configured production frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # CRA dev server
        FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """
    Pre-load the heavy AI models (PyTorch/SentenceTransformers) during boot.
    Render allows up to 10 minutes for boot, but only 100 seconds for a request.
    If we lazy-load on the first request, Render throws a 502 Bad Gateway timeout.
    """
    print("[Startup] Pre-loading RAG service models to prevent 502 timeouts...", flush=True)
    try:
        rag_service._initialize()
        print("[Startup] RAG service loaded successfully.", flush=True)
    except Exception as e:
        print(f"[Startup] Failed to load RAG service: {e}", flush=True)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router.router)
app.include_router(conversations_router.router)
app.include_router(chat_router.router)


@app.get("/", tags=["health"])
def health():
    return {"status": "ok", "service": "GraphMind API"}
