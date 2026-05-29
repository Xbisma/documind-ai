def build_chunk_id(chunk: Dict) -> str:
    """
    Builds a stable unique ID for every chunk.
    This helps prevent duplicate chunks when the same PDF is uploaded again.

    IMPORTANT: include session_id + doc_id so different chats don't collide.
    """
    raw_id = (
        f"{chunk.get('session_id','')}|"
        f"{chunk.get('doc_id','')}|"
        f"{chunk['doc_name']}|"
        f"{chunk['page_number']}|"
        f"{chunk['page_chunk_index']}|"
        f"{chunk['text'][:100]}"
    )
    return hashlib.sha256(raw_id.encode("utf-8")).hexdigest()

def embed_and_store(chunks: List[Dict], collection_name: str = "documents") -> Dict:
    collection = get_chroma_collection(collection_name)

    new_chunks = filter_new_chunks(collection, chunks)

    if not new_chunks:
        return {
            "received_chunks": len(chunks),
            "stored_chunks": 0,
            "skipped_duplicates": len(chunks)
        }

    texts = [chunk["text"] for chunk in new_chunks]

    print(f"[Embedder] Generating embeddings for {len(texts)} chunks...")

    embeddings = embed_texts(texts)

    metadatas = []
    ids = []

    uploaded_at = datetime.now(timezone.utc).isoformat()

    for chunk in new_chunks:
        # Ensure chunk_id exists and is stable
        if not chunk.get("chunk_id"):
            chunk["chunk_id"] = build_chunk_id(chunk)

        ids.append(chunk["chunk_id"])

        metadatas.append({
            "chunk_id": chunk["chunk_id"],

            # NEW: session/document scoping fields
            "session_id": chunk.get("session_id"),
            "doc_id": chunk.get("doc_id"),

            "doc_name": chunk["doc_name"],
            "source_path": chunk.get("source_path", ""),
            "page_number": str(chunk["page_number"]),
            "page_chunk_index": str(chunk["page_chunk_index"]),
            "global_chunk_index": str(chunk["global_chunk_index"]),
            "snippet": chunk["snippet"],
            "char_count": str(chunk["char_count"]),

            # NEW: highlight anchors (may be None)
            "char_start": "" if chunk.get("char_start") is None else str(chunk.get("char_start")),
            "char_end": "" if chunk.get("char_end") is None else str(chunk.get("char_end")),

            "uploaded_at": uploaded_at,
            "embedding_model": EMBEDDING_MODEL_NAME
        })

    collection.add(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

    print(f"[Embedder] Stored {len(new_chunks)} new chunks in ChromaDB.")

    return {
        "received_chunks": len(chunks),
        "stored_chunks": len(new_chunks),
        "skipped_duplicates": len(chunks) - len(new_chunks)
    }