import requests
from typing import Any, Dict, List, Optional

BACKEND_URL = "http://127.0.0.1:8000"


def upload_pdfs(
    files: List[tuple],
    session_id: Optional[str] = None
) -> Dict[str, Any]:

    params = {}

    if session_id:
        params["session_id"] = session_id

    r = requests.post(
        f"{BACKEND_URL}/upload-pdfs/",
        params=params,
        files=files,
        timeout=300,
    )

    r.raise_for_status()
    return r.json()


def search_test(
    query: str,
    session_id: Optional[str],
    top_k: int,
    min_similarity: float
) -> Dict[str, Any]:

    params = {
        "q": query,
        "top_k": top_k,
        "min_similarity": min_similarity,
    }

    if session_id:
        params["session_id"] = session_id

    r = requests.get(
        f"{BACKEND_URL}/search-test/",
        params=params,
        timeout=120,
    )

    r.raise_for_status()
    return r.json()


def ask(question: str, session_id: str) -> Dict[str, Any]:
    r = requests.post(
        f"{BACKEND_URL}/ask",
        json={
            "question": question,
            "session_id": session_id,
        },
        timeout=180,
    )

    r.raise_for_status()
    return r.json()