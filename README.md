# MineCatalog Support Assistant

Asistente automatizado de soporte técnico para el software MineCatalog. Responde preguntas utilizando la documentación técnica mediante un pipeline RAG (Retrieval-Augmented Generation).

## Arquitectura

```
Usuario → n8n Webhook (:5678) → HTTP POST → FastAPI /ask (:8000) → 
  chunk search (ChromaDB + sentence-transformers) → 
  prompt → Gemini (gemini-2.5-flash) → respuesta → n8n → usuario
```

## Requisitos

- Python 3.10+
- [n8n](https://n8n.io/) (para el workflow, opcional con Docker)
- [Docker](https://docker.com/) (opcional, para levantar todo con un comando)
- Gemini API Key (gratuita en [Google AI Studio](https://aistudio.google.com/))

## Instalación

### Opción A — Con Docker (recomendado)

```bash
# 1. Clonar y configurar
cp .env.example .env
# Editar .env y agregar GEMINI_API_KEY

# 2. Levantar todo
docker-compose up
```

Esto levanta el backend en `http://localhost:8000` y n8n en `http://localhost:5678`.
Para n8n en Docker, importar el workflow `n8n/support_assistant_docker.json` (usa la URL interna del contenedor).

### Opción B — Manual (sin Docker)

```bash
# 1. Entorno virtual
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# 2. Dependencias
pip install -r requirements.txt

# 3. Configurar .env
cp .env.example .env
# Editar .env y agregar GEMINI_API_KEY

# 4. Indexar documentos
python scripts/ingest_docs.py

# 5. Iniciar servidor (Terminal 1)
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

El workflow se compone de 2 nodos:
- **Webhook**: recibe POST en `/webhook/chat-support`
- **Ask Backend**: reenvía la pregunta al backend Python

### Configuración de nodos

| Nodo | Campo | Valor |
|------|-------|-------|
| Webhook | Path | `chat-support` |
| Ask Backend | Method | POST |
| Ask Backend | URL | `http://127.0.0.1:8000/ask` |
| Ask Backend | Body Content Type | JSON |
| Ask Backend | Specified Body | `{"question": "{{ $json.question }}"}` |
| Ask Backend | Timeout | 30000 |

> **Importante:** usar `127.0.0.1` en vez de `localhost` porque n8n resuelve localhost como IPv6.
>
> Si usás Docker, importá `n8n/support_assistant_docker.json` (usa `http://backend:8000/ask`).

### Probar el workflow

1. Abrir n8n (`http://localhost:5678`).
2. Ir a **Workflows** → importar `n8n/support_assistant.json`.
3. Hacer click en **Execute Workflow** (▶).
4. Probar en modo test:
   ```
   Invoke-RestMethod -Uri http://localhost:5678/webhook-test/chat-support -Method POST -ContentType "application/json" -Body '{"question":"¿Cómo soluciono error de conexión a la BD?"}'
   ```
5. Si funciona, click en **Publish** para habilitar la URL de producción:
   ```
   Invoke-RestMethod -Uri http://localhost:5678/webhook/chat-support -Method POST -ContentType "application/json" -Body '{"question":"¿Cómo soluciono error de conexión a la BD?"}'
   ```

## Frontend Web

Abrir `frontend/index.html` en el navegador (con el backend corriendo). Interfaz de chat que consume `POST /ask`.

## Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

Incluye tests de:
- **Ingestión**: limpieza de texto, chunking con overlap
- **API**: health check, preguntas vacías, endpoints `/ask` e `/ingest`
- **Pipeline**: preguntas sin contexto, fallback, casos borde

## Estructura del proyecto

```
├── backend/
│   ├── main.py            # FastAPI entry point
│   ├── config.py          # Configuración desde .env
│   ├── models.py          # Schemas Pydantic
│   ├── ingestion.py       # Lectura, limpieza y chunking
│   ├── embeddings.py      # sentence-transformers wrapper
│   ├── vector_store.py    # ChromaDB store & search
│   └── rag_pipeline.py    # Pipeline RAG (retrieve + Gemini)
├── frontend/
│   └── index.html         # Chat UI (abrir en navegador)
├── scripts/
│   └── ingest_docs.py     # Script para poblar ChromaDB
├── tests/
│   ├── conftest.py        # Configuración de tests
│   ├── test_ingestion.py  # Tests de limpieza y chunking
│   ├── test_api.py        # Tests de endpoints HTTP
│   └── test_pipeline.py   # Tests del pipeline RAG
├── n8n/
│   ├── support_assistant.json         # Workflow n8n (local)
│   └── support_assistant_docker.json  # Workflow n8n (Docker)
├── docs/                  # Documentación fuente
├── Dockerfile             # Imagen Docker del backend
├── docker-compose.yml     # Backend + n8n en contenedores
├── .dockerignore
├── .env.example
├── requirements.txt
└── README.md
```

## Manejo de errores

- **Pregunta vacía**: devuelve 400 con mensaje claro.
- **Sin información relevante**: responde "No tengo información disponible en la documentación para responder esa consulta."
- **Error de autenticación Gemini**: responde indicando que la API key es inválida.
- **Cuota agotada (429)**: responde indicando que se superó el límite de uso gratuito (el backend reintenta hasta 3 veces automáticamente).
- **Servicio no disponible (503)**: responde indicando congestión temporal (reintento automático incluido).
- **Error de conexión**: responde indicando problema de red o clave API.
- **ECONNREFUSED ::1:8000**: n8n usó IPv6; cambiar `localhost` por `127.0.0.1` en la URL del nodo HTTP.
- **Docker — conexión rechazada**: Si n8n en Docker no llega al backend, verificar que ambos estén en la misma red (`depends_on` en docker-compose) y usar `http://backend:8000/ask`.
- **Documentación no encontrada**: se maneja con logging.
