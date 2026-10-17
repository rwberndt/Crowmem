from functools import lru_cache
from threading import Lock

from fastembed import TextEmbedding

_MODEL_NAME = "BAAI/bge-small-en-v1.5"
_DIMENSION = 384


class FastEmbedClient:
    def __init__(self) -> None:
        self._model: TextEmbedding | None = None
        self._init_lock = Lock()

    def embed(self, text: str) -> list[float]:
        if self._model is None:
            with self._init_lock:
                if self._model is None:
                    self._model = TextEmbedding(model_name=_MODEL_NAME)
        (vector,) = self._model.embed([text])
        return vector.tolist()

    @property
    def dimension(self) -> int:
        return _DIMENSION


@lru_cache
def get_embedding_client() -> FastEmbedClient:
    return FastEmbedClient()
