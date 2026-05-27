from backend.services.query_rewriter import rewrite_query


def test_query_rewriter_install_question():
    query = "How do I install it?"
    rewritten = rewrite_query(query)

    assert rewritten == "installation steps"


def test_query_rewriter_normal_question():
    query = "What is ChromaDB?"
    rewritten = rewrite_query(query)

    assert rewritten == "What is ChromaDB?"