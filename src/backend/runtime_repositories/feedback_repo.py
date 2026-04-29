from __future__ import annotations

from core.firebase import get_db, is_firebase_enabled
from models.schemas import FeedbackEntry


class FeedbackRepository:
    def __init__(self) -> None:
        self.items: dict[str, FeedbackEntry] = {}
        self.persistence_enabled = True

    def save(self, entry: FeedbackEntry) -> None:
        self.items[entry.id] = entry
        if not self.persistence_enabled or not is_firebase_enabled():
            return

        try:
            self._feedback_collection().document(entry.id).set(entry.model_dump(), timeout=5)
        except Exception:
            self.persistence_enabled = False

    def list(self, limit: int = 100) -> list[FeedbackEntry]:
        if self.persistence_enabled and is_firebase_enabled():
            try:
                snaps = (
                    self._feedback_collection()
                    .order_by("created_at", direction="DESCENDING")
                    .limit(limit)
                    .stream()
                )
                items = [FeedbackEntry.model_validate(snap.to_dict() or {}) for snap in snaps]
                for entry in items:
                    self.items[entry.id] = entry
                return items
            except Exception:
                self.persistence_enabled = False

        items = sorted(self.items.values(), key=lambda item: item.created_at, reverse=True)
        return items[:limit]

    def _feedback_collection(self):
        return get_db().collection("feedback")


feedback_repo = FeedbackRepository()