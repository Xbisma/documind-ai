import json
import os
from datetime import datetime, timezone
from typing import Dict, Any

REGISTRY_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../storage/docs_registry.json")
)

def _ensure_registry_file():
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    if not os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)

def register_document(session_id: str, doc_id: str, doc_name: str, source_path: str) -> Dict[str, Any]:
    _ensure_registry_file()
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f) or {}

    session_docs = data.get(session_id, {})
    session_docs[doc_id] = {
        "doc_id": doc_id,
        "doc_name": doc_name,
        "source_path": source_path,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    data[session_id] = session_docs

    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return session_docs[doc_id]