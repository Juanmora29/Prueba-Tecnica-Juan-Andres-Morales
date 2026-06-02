from functools import lru_cache

from sentence_transformers import SentenceTransformer

from backend.config import settings


def _is_e5_model(model_name: str) -> bool:
    return "e5-" in model_name.lower() or model_name.lower().endswith("-e5")


def _prefix_for_model(model_name: str) -> tuple[str, str]:
    if _is_e5_model(model_name):
        return ("query: ", "passage: ")
    return ("", "")


class EmbeddingsModel:
    def __init__(self, model_name: str = None):
        if model_name is None:
            model_name = settings.embedding_model
        self.model_name = model_name
        self._model = None
        query_prefix, passage_prefix = _prefix_for_model(model_name)
        self.query_prefix = query_prefix
        self.passage_prefix = passage_prefix

    def _load(self):
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        self._load()
        prefixed = [f"{self.passage_prefix}{t}" for t in texts]
        embeddings = self._model.encode(prefixed, show_progress_bar=False)
        return embeddings.tolist()

    def encode_query(self, text: str) -> list[float]:
        self._load()
        prefixed = f"{self.query_prefix}{text}"
        embedding = self._model.encode([prefixed], show_progress_bar=False)
        return embedding[0].tolist()

    def get_dimension(self) -> int:
        self._load()
        return self._model.get_sentence_embedding_dimension()


@lru_cache(maxsize=1)
def get_embeddings_model() -> EmbeddingsModel:
    return EmbeddingsModel()
