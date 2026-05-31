import logging

import openai
from openai import OpenAI

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
        self._openai = None

    def _get_client(self) -> OpenAI:
        if self._openai is None:
            if not settings.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY is not set in .env file"
                )
            self._openai = OpenAI(api_key=settings.openai_api_key)
        return self._openai

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
        try:
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Contexto de la documentación:\n\n{context}\n\n"
                            f"Pregunta del usuario: {question}"
                        ),
                    },
                ],
                temperature=0,
                max_tokens=500,
                timeout=30,
            )
        except openai.AuthenticationError:
            logger.error("OpenAI authentication failed — invalid API key")
            return (
                "Error de autenticación con OpenAI. "
                "Verifica que la clave API en el archivo .env sea correcta."
            )
        except openai.RateLimitError:
            logger.error("OpenAI rate limit exceeded")
            return (
                "Se ha excedido el límite de solicitudes a OpenAI. "
                "Espera unos minutos e inténtalo de nuevo."
            )
        except openai.APITimeoutError:
            logger.error("OpenAI request timed out")
            return (
                "La solicitud a OpenAI tardó demasiado en responder. "
                "Verifica tu conexión a internet e inténtalo de nuevo."
            )
        except openai.APIConnectionError:
            logger.error("OpenAI connection error")
            return (
                "No se pudo conectar con OpenAI. "
                "Verifica tu conexión a internet."
            )
        except openai.APIError as e:
            logger.exception(f"OpenAI API error: {e}")
            return (
                "Ocurrió un error inesperado al comunicarse con OpenAI. "
                "Inténtalo de nuevo más tarde."
            )

        return response.choices[0].message.content.strip()

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
