# DocuMind AI
## RAG Question Answering Module

This module handles:

- Query rewriting for vague user questions
- Vector retrieval from ChromaDB
- Relevance score threshold filtering
- Context-based answer generation using Groq LLM
- Prompt rules to reduce hallucination
- Citation output with document name, page number, snippet, and relevance score

### API Endpoint

POST `/ask`

Request:

```json
{
  "question": "How do I install it?"
}
```

Response:

```json
{
  "answer": "...",
  "rewritten_query": "installation steps",
  "citations": [],
  "status": "answered"
}
```