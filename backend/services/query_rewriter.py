from typing import Optional


def rewrite_query(user_query: str, chat_context: Optional[str] = None) -> str:
    """
    Rewrites vague user queries into clearer search queries.

    For now, this is rule-based.
    Later, this can be replaced with an LLM-based rewriter.
    """

    if not user_query or not user_query.strip():
        return ""

    query = user_query.strip()

    vague_phrases = {
        "how do i install it": "installation steps",
        "how to install it": "installation steps",
        "install it": "installation steps",
        "setup it": "setup instructions",
        "how to setup": "setup instructions",
        "what is this": "definition explanation",
        "how does it work": "working mechanism explanation",
        "fix this": "troubleshooting steps",
        "error": "error troubleshooting solution",
    }

    lower_query = query.lower()

    for vague, improved in vague_phrases.items():
        if vague in lower_query:
            return improved

    if chat_context:
        return f"{query} Context: {chat_context}"

    return query