"""Firestore RunStore — the cloud history store (Phase 14 on Cloud Run; free quota). Collection `runs`,
one document per run. Credentials come from the environment (Cloud Run service account, or
`gcloud auth application-default login` locally); FIRESTORE_EMULATOR_HOST switches to the local emulator."""
from google.cloud import firestore

from app.storage.base import RunRecord, now_iso


class FirestoreRunStore:
    def __init__(self, project: str | None, collection: str = "runs"):
        self._col = firestore.Client(project=project).collection(collection)

    def create(self, rec: RunRecord) -> None:
        self._col.document(rec.run_id).set(rec.model_dump(mode="json"))

    def update(self, run_id: str, **fields) -> None:
        doc = self._col.document(run_id)
        if not doc.get().exists:
            return
        # merge=True updates only the given top-level fields (snapshot is replaced as a whole, by design)
        doc.set({**fields, "updated_at": now_iso()}, merge=True)

    def get(self, run_id: str) -> RunRecord | None:
        snap = self._col.document(run_id).get()
        return RunRecord.model_validate(snap.to_dict()) if snap.exists else None

    def list(self, limit: int = 50) -> list[RunRecord]:
        q = self._col.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
        return [RunRecord.model_validate(d.to_dict()) for d in q.stream()]
