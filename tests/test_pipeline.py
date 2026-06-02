from unittest.mock import patch

from backend.rag_pipeline import RAGPipeline


def test_answer_empty_question():
    pipeline = RAGPipeline()
    result = pipeline.answer("")
    assert result["answer"] == "Por favor, escribe una pregunta válida."


def test_answer_whitespace_question():
    pipeline = RAGPipeline()
    result = pipeline.answer("   ")
    assert result["answer"] == "Por favor, escribe una pregunta válida."


def test_answer_no_context_returns_fallback():
    pipeline = RAGPipeline()

    with patch.object(pipeline.vector_store, "search", return_value=[]):
        result = pipeline.answer("pregunta sin contexto")

    assert "No tengo información disponible" in result["answer"]
    assert result["sources"] == []


def test_generate_no_chunks():
    pipeline = RAGPipeline()
    msg = pipeline.generate("test", [])
    assert "No tengo información disponible" in msg
