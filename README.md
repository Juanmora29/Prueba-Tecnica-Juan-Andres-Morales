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
- [n8n](https://n8n.io/) (para el workflow)
- Gemini API Key (gratuita en [Google AI Studio](https://aistudio.google.com/))

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
# Editar .env y agregar GEMINI_API_KEY

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
- **Error de autenticación Gemini**: responde indicando que la API key es inválida.
- **Cuota agotada (429)**: responde indicando que se superó el límite de uso gratuito (el backend reintenta hasta 3 veces automáticamente).
- **Servicio no disponible (503)**: responde indicando congestión temporal (reintento automático incluido).
- **Error de conexión**: responde indicando problema de red o clave API.
- **ECONNREFUSED ::1:8000**: n8n usó IPv6; cambiar `localhost` por `127.0.0.1` en la URL del nodo HTTP.
- **Documentación no encontrada**: se maneja con logging.
