import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.ingestion import process_documents
from backend.models import AskRequest, AskResponse, ErrorResponse
from backend.rag_pipeline import RAGPipeline
from backend.vector_store import VectorStore

logger = logging.getLogger(__name__)

pipeline: RAGPipeline | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    logger.info("Starting up: ingesting documents and initializing pipeline...")
    try:
        chunks = process_documents()
        store = VectorStore()
        store.index_documents(chunks)
        logger.info(f"Indexed {len(chunks)} chunks from documentation")
    except Exception as e:
        logger.warning(f"Could not index documents on startup: {e}")
    pipeline = RAGPipeline()
    yield


app = FastAPI(
    title="MineCatalog Support Assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post(
    "/ask",
    response_model=AskResponse,
    responses={500: {"model": ErrorResponse}},
)
def ask(request: AskRequest):
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="La pregunta no puede estar vacía",
        )
    try:
        result = pipeline.answer(request.question)
        return AskResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Error processing question")
        raise HTTPException(
            status_code=500,
            detail="Error interno al procesar la pregunta",
        )


@app.post("/ingest")
def ingest():
    try:
        chunks = process_documents()
        store = VectorStore()
        store.index_documents(chunks)
        return {"status": "ok", "chunks_indexed": len(chunks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    try:
        store = VectorStore()
        count = store.count()
        return {
            "status": "ok",
            "chunks_count": count,
            "embedding_model": settings.embedding_model,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host=settings.host, port=settings.port, reload=True)
