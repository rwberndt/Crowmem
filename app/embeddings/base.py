from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingClient(Protocol):
    """Provider-agnostic embedding interface. Swap implementations via EMBEDDING_PROVIDER."""

    def embed(self, text: str) -> list[float]: ...

    @property
    def dimension(self) -> int: ...
