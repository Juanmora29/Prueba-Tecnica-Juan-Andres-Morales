# MineCatalog Support Assistant

Asistente automatizado de soporte técnico para el software MineCatalog. Responde preguntas utilizando la documentación técnica mediante un pipeline RAG (Retrieval-Augmented Generation).

## Arquitectura

```
Usuario → n8n Webhook → HTTP POST → FastAPI /ask → 
  chunk search (ChromaDB + sentence-transformers) → 
  prompt → OpenAI GPT → respuesta → n8n → usuario
```

## Requisitos

- Python 3.10+
- [n8n](https://n8n.io/) (para el workflow)
- OpenAI API Key (para generación de respuestas)

## Instalación

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd <repo-dir>

# 2. Crear entorno virtual e instalar dependencias
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt

# Si usás Python 3.14 (última versión), agregá --pre:
# pip install --pre -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env y agregar OPENAI_API_KEY

# 4. Poblar la base de datos vectorial
python scripts/ingest_docs.py

# 5. Iniciar el servidor
python -m backend.main
```

El servidor corre en `http://localhost:8000`.

## API Endpoints

### `POST /ask`
Envía una pregunta al asistente.

```json
{
  "question": "¿Cómo reinicio el servicio de autenticación?"
}
```

Respuesta:
```json
{
  "answer": "Respuesta basada en la documentación...",
  "sources": [
    {
      "document": "Documentación 2.txt",
      "content": "Fragmento relevante...",
      "score": 0.92
    }
  ]
}
```

### `POST /ingest`
Refresca el índice con los documentos actuales de `docs/`.

### `GET /health`
Health check del servicio.

## n8n Workflow

1. Abrir n8n (`http://localhost:5678`).
2. Importar el workflow desde `n8n/support_assistant.json`.
3. Activar el workflow.
4. Hacer POST a `http://localhost:5678/webhook/minecatalog-chat` con:
   ```json
   { "question": "¿Cómo soluciono error de conexión a la BD?" }
   ```

## Estructura del proyecto

```
├── backend/
│   ├── main.py            # FastAPI entry point
│   ├── config.py          # Configuración desde .env
│   ├── models.py          # Schemas Pydantic
│   ├── ingestion.py       # Lectura, limpieza y chunking
│   ├── embeddings.py      # sentence-transformers wrapper
│   ├── vector_store.py    # ChromaDB store & search
│   └── rag_pipeline.py    # Pipeline RAG (retrieve + OpenAI)
├── scripts/
│   └── ingest_docs.py     # Script para poblar ChromaDB
├── n8n/
│   └── support_assistant.json  # Workflow n8n exportado
├── docs/                  # Documentación fuente
├── .env.example
├── requirements.txt
└── README.md
```

## Manejo de errores

- **Pregunta vacía**: devuelve 400 con mensaje claro.
- **Sin información relevante**: responde "No tengo información disponible en la documentación para responder esa consulta."
- **Error de autenticación OpenAI**: responde indicando que la API key es inválida (no expone la key).
- **Rate limit OpenAI**: responde sugiriendo esperar e intentar de nuevo.
- **Timeout OpenAI**: responde indicando problema de conexión.
- **Error de conexión OpenAI**: responde indicando problema de red.
- **Documentación no encontrada**: se maneja con logging.
