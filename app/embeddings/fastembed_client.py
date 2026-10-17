from functools import lru_cache

from fastembed import TextEmbedding

_MODEL_NAME = "BAAI/bge-small-en-v1.5"
_DIMENSION = 384


class FastEmbedClient:
    def __init__(self) -> None:
        self._model = TextEmbedding(model_name=_MODEL_NAME)

    def embed(self, text: str) -> list[float]:
        (vector,) = self._model.embed([text])
        return vector.tolist()

    @property
    def dimension(self) -> int:
        return _DIMENSION


@lru_cache
def get_embedding_client() -> FastEmbedClient:
    return FastEmbedClient()
