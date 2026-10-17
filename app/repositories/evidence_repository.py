from sqlalchemy.orm import Session

from app.models.evidence import Evidence


class EvidenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, evidence: Evidence) -> Evidence:
        self.db.add(evidence)
        self.db.flush()
        return evidence
