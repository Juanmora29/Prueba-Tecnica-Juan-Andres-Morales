# MineCatalog Support Assistant

Asistente automatizado de soporte técnico para el software MineCatalog. Responde preguntas utilizando la documentación técnica mediante un pipeline RAG (Retrieval-Augmented Generation) con doble capa de inferencia: Gemini API + Ollama como fallback local.

## Arquitectura

```
Usuario → n8n Webhook (:5678) → HTTP POST → FastAPI /ask (:8000) →
  chunk search (ChromaDB + multilingual-e5-small embeddings) →
  prompt → Gemini (gemini-2.5-flash) ──┬─ OK → respuesta → n8n → usuario
                                        └─ 429/503 → Ollama (llama3.2:3b) → respuesta
```

## Requisitos

- Python 3.10+
- [n8n](https://n8n.io/) (para el workflow, opcional con Docker)
- [Docker](https://docker.com/) (opcional, para levantar todo con un comando)
- Gemini API Key (gratuita en [Google AI Studio](https://aistudio.google.com/))
- [Ollama](https://ollama.com/) (opcional, para fallback local sin cuota)

## Instalación

### Opción A — Con Docker (recomendado)

```bash
# 1. Clonar y configurar
cp .env.example .env
# Editar .env y agregar GEMINI_API_KEY

# 2. Levantar todo (primera vez: ~5min por descarga de modelos)
docker-compose up --build
```

> El primer build descarga el modelo de embeddings (multilingual-e5-small).
> Builds posteriores usan caché y son casi instantáneos.

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

### Fallback local con Ollama (opcional)

Cuando Gemini alcanza el límite de cuota gratuita (1500 req/día), el sistema
cae automáticamente a un modelo local vía Ollama.

```bash
# 1. Instalar Ollama (https://ollama.com/)
# 2. Descargar el modelo
ollama pull llama3.2:3b

# 3. Activar en .env
LOCAL_FALLBACK_ENABLED=true
LOCAL_MODEL_NAME=llama3.2:3b
OLLAMA_URL=http://localhost:11434/api/generate

# 4. Reiniciar el backend
python -m backend.main
```

> **En Linux con Docker:** el `docker-compose.yml` usa `network_mode: host` y
> `http://localhost:11434/api/generate`. Además, Ollama debe escuchar en
> `0.0.0.0` (configurar con `OLLAMA_HOST=0.0.0.0` en systemd o al iniciarlo).
>
> **En Mac/Windows con Docker Desktop:** funciona con `host.docker.internal`
> (el nombre DNS que Docker resuelve automáticamente a la IP del host).
> Si se quiere usar `bridge` en vez de `host`, cambiar `OLLAMA_URL` a
> `http://host.docker.internal:11434/api/generate`.

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

| Nodo        | Campo             | Valor                                  |
| ----------- | ----------------- | -------------------------------------- |
| Webhook     | Path              | `chat-support`                         |
| Ask Backend | Method            | POST                                   |
| Ask Backend | URL               | `http://127.0.0.1:8000/ask`            |
| Ask Backend | Body Content Type | JSON                                   |
| Ask Backend | Specified Body    | `{"question": "{{ $json.question }}"}` |
| Ask Backend | Timeout           | 30000                                  |

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

El frontend es un archivo HTML local (no requiere servidor web). Con el backend corriendo:

1. Abrí el Explorador de archivos en la carpeta del proyecto
2. Hacé doble click en `frontend/index.html`
   (O abrí el navegador y presioná Ctrl+O → seleccioná el archivo)

Se abre una interfaz de chat que consume `POST /ask`. Escribí una pregunta y presioná Enter o click en "Enviar".

> El backend debe estar corriendo en `http://localhost:8000` (Docker o manual).
> El CORS ya está habilitado, funciona directo desde el archivo local.

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
│   ├── embeddings.py      # sentence-transformers wrapper (e5 con prefijos query/passage)
│   ├── vector_store.py    # ChromaDB store & search
│   └── rag_pipeline.py    # Pipeline RAG (retrieve + Gemini + Ollama fallback)
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
- **Cuota agotada (429)**: si `LOCAL_FALLBACK_ENABLED=true` y Ollama está instalado, responde con el modelo local. Sino, indica que se superó el límite gratuito.
- **Servicio no disponible (503)**: mismo comportamiento: si el fallback local está activo, responde con Ollama.
- **Error de conexión**: responde indicando problema de red o clave API.
- **ECONNREFUSED ::1:8000**: n8n usó IPv6; cambiar `localhost` por `127.0.0.1` en la URL del nodo HTTP.
- **Docker — conexión rechazada**: Si n8n en Docker no llega al backend, verificar que ambos estén en la misma red (`depends_on` en docker-compose) y usar `http://backend:8000/ask`.
- **Documentación no encontrada**: se maneja con logging.
