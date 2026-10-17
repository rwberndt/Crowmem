"""Importing this package registers every model on Base.metadata, so any
code that touches one model (e.g. a cross-table FK) never hits an
unresolved-table error from a partial import.
"""

from app.models.base import Base  # noqa: F401
from app.models import (  # noqa: F401
    episode,
    memory,
    belief,
    evidence,
    association,
    memory_usage,
    retrieval_log,
    usage_log,
)
