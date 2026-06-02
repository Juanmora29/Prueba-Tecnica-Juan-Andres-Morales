import logging
import time

from google import genai
from google.genai import types as genai_types
from google.genai import errors as genai_errors

from backend.config import settings
from backend.vector_store import VectorStore

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "Eres un asistente de soporte técnico especializado en el software MineCatalog. "
    "Tu función es responder preguntas de los usuarios utilizando ÚNICAMENTE la "
    "documentación técnica proporcionada como contexto.\n\n"
    "REGLAS:\n"
    "1. Responde siempre en español, de forma clara y concisa.\n"
    "2. Usa exclusivamente la información del contexto que se te proporciona.\n"
    "3. Si la información solicitada NO está en el contexto, responde: "
    "'No tengo información disponible en la documentación para responder esa consulta.'\n"
    "4. No inventes datos, procedimientos, códigos de error o soluciones.\n"
    "5. Si es relevante, menciona el nombre del documento del que obtuviste la información.\n"
    "6. Si la pregunta está vacía o no es clara, solicita más detalles al usuario."
)


class RAGPipeline:
    def __init__(self):
        self.vector_store = VectorStore()
        self._client = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            if not settings.gemini_api_key:
                raise ValueError(
                    "GEMINI_API_KEY is not set in .env file"
                )
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    def retrieve(self, question: str) -> list[dict]:
        return self.vector_store.search(question)

    def generate(self, question: str, context_chunks: list[dict]) -> str:
        if not context_chunks:
            return (
                "No tengo información disponible en la documentación "
                "para responder esa consulta."
            )

        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            context_parts.append(
                f"[Documento: {chunk['document']}]\n{chunk['content']}"
            )
        context = "\n\n".join(context_parts)

        client = self._get_client()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=settings.gemini_model,
                    contents=(
                        f"Contexto de la documentación:\n\n{context}\n\n"
                        f"Pregunta del usuario: {question}"
                    ),
                    config=genai_types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0,
                        max_output_tokens=500,
                    ),
                )
                break
            except genai_errors.ClientError as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    if attempt < max_retries - 1:
                        retry_after = 5 * (attempt + 1)
                        logger.warning(
                            f"Gemini rate limited (attempt {attempt+1}), "
                            f"retrying in {retry_after}s..."
                        )
                        time.sleep(retry_after)
                        continue
                    return (
                        "Se agotó la cuota gratuita de Gemini. "
                        "Esperá unos minutos e intentá de nuevo."
                    )
                logger.exception(f"Gemini API client error: {e}")
                return (
                    "Ocurrió un error al comunicarse con Gemini. "
                    "Verificá la clave API en el archivo .env."
                )
            except genai_errors.ServerError as e:
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    if attempt < max_retries - 1:
                        retry_after = 5 * (attempt + 1)
                        logger.warning(
                            f"Gemini unavailable (attempt {attempt+1}), "
                            f"retrying in {retry_after}s..."
                        )
                        time.sleep(retry_after)
                        continue
                    return (
                        "El servicio Gemini está temporalmente congestionado. "
                        "Intentá de nuevo en unos minutos."
                    )
                logger.exception(f"Gemini API server error: {e}")
                return (
                    "Ocurrió un error en el servidor de Gemini. "
                    "Intentá de nuevo más tarde."
                )
            except Exception as e:
                logger.exception(f"Gemini API error: {e}")
                return (
                    "Ocurrió un error al comunicarse con Gemini. "
                    "Verificá tu conexión a internet."
                )

        if not response.text:
            return (
                "Gemini no generó una respuesta. "
                "Inténtalo de nuevo más tarde."
            )

        return response.text.strip()

    def answer(self, question: str) -> dict:
        if not question or not question.strip():
            return {
                "answer": "Por favor, escribe una pregunta válida.",
                "sources": [],
            }

        retrieved = self.retrieve(question)

        answer_text = self.generate(question, retrieved)

        sources = [
            {
                "document": r["document"],
                "content": r["content"][:200],
                "score": r["score"],
            }
            for r in retrieved
        ]

        return {"answer": answer_text, "sources": sources}
