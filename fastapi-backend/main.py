from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import documents, auth
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    handlers=[
        logging.FileHandler("audit.log"),
        logging.StreamHandler()
    ]
)

app = FastAPI(
    title="MED AI Document Processing API",
    description="Backend API for FDA 3500 MedWatch document processing pipeline",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "MED AI FastAPI Backend", "docs": "/docs"}

@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
