from functools import lru_cache

from sentence_transformers import SentenceTransformer

from backend.config import settings


class EmbeddingsModel:
    def __init__(self, model_name: str = None):
        if model_name is None:
            model_name = settings.embedding_model
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        self._load()
        embeddings = self._model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def encode_query(self, text: str) -> list[float]:
        return self.encode([text])[0]

    def get_dimension(self) -> int:
        self._load()
        return self._model.get_sentence_embedding_dimension()


@lru_cache(maxsize=1)
def get_embeddings_model() -> EmbeddingsModel:
    return EmbeddingsModel()
