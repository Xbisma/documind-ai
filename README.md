# DocuMind AI

DocuMind AI is a RAG-based technical documentation assistant. It allows users to upload PDF documents, process them into searchable chunks, and ask questions based on the uploaded content.

The system retrieves relevant document chunks from a vector database and generates answers with citations to reduce hallucination.

---

## Main Features

- Multi-PDF upload support
- PDF text extraction using PyMuPDF
- Text cleaning and preprocessing
- Chunking with overlap for better context preservation
- Embedding generation using Sentence Transformers
- Vector storage using ChromaDB
- Duplicate chunk detection
- Semantic retrieval with relevance score filtering
- Query rewriting for vague questions
- Context-based answer generation using Groq LLM
- Citation output with document name, page number, snippet, and relevance score

---

## Project Modules

### 1. PDF Processing and Ingestion Module

This module handles the document upload and preparation pipeline.

It includes:

- Uploading one or multiple PDF files
- Saving uploaded PDFs locally
- Extracting text page by page
- Cleaning extracted PDF text
- Splitting text into chunks
- Preserving citation metadata
- Generating embeddings
- Storing chunks and metadata in ChromaDB
- Skipping duplicate chunks when the same PDF is uploaded again

Pipeline:

```text
PDF Upload
→ Save PDF
→ Extract Text
→ Clean Text
→ Chunk Text
→ Generate Embeddings
→ Store in ChromaDB
```

Important metadata stored with each chunk:

```text
doc_name
source_path
page_number
page_chunk_index
global_chunk_index
snippet
char_count
uploaded_at
embedding_model

```


### 2. RAG Question Answering Module

This module handles user questions and answer generation.

It includes:

- Query rewriting for vague user questions
- Vector retrieval from ChromaDB
- Relevance score threshold filtering
- Context-based answer generation using Groq LLM
- Prompt rules to reduce hallucination
- Citation output with document name, page number, snippet, and relevance score

Pipeline:

```text
User Question
→ Rewrite Query
→ Retrieve Relevant Chunks
→ Apply Similarity Threshold
→ Build Context
→ Generate Answer
→ Return Answer with Citations
```

#### API Endpoint

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

## Tech  Stack

### Backend
- FastAPI
- PyMuPDF
- LangChain text splitters
- Sentence Transformers
- ChromaDB
- Groq API

### Frontend
- Streamlit

### Other Tools
- Python
- Git and GitHub
- dotenv for environment variables

## Folder Structure
```
documind-ai/
│
├── backend/
|   ├── __init__.py
│   ├── main.py
|   ├── tests/
|       ├── test_rag_flow.py
│   └── services/
│       ├── __init__.py
│       ├── pdf_pipeline.py
│       ├── pdf_extractor.py
│       ├── text_cleaner.py
│       ├── chunker.py
│       ├── embedder.py
│       └── retriever.py
|       └── prompt_templates.py
|       └── query_rewriter.py
|       └── rag_chain.py
│
├── frontend/
│   └── app.py
│
├── chroma_db/              # generated locally, ignored by git
├── requirements.txt
├── .env              # ignored by git
├── .gitignore
└── README.md
```

## How to Run the Project

### 1. Clone the repository

```bash
git clone https://github.com/Xbisma/documind-ai
cd documind-ai
```

### 2. Create virtual environment

```bash
python -m venv venv
```

Activate it:
```bash
venv\Scripts\activate
```

For macOS/Linux:
```bash
source venv\bin\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start backend

```bash
uvicorn backend.main:app --reload
```

Backend runs at:
```
http://127.0.0.1:8000
```

Swagger docs:
```
http://127.0.0.1:8000/docs
```

### 5. Start Frontend

Open a new terminal:
```bash
streamlit run frontend/app.py
```

Basic Usage Flow
```text
1. Start FastAPI backend
2. Start Streamlit frontend
3. Upload one or multiple PDFs
4. Wait for PDF processing to complete
5. Ask a question from uploaded documents
6. View answer and citations
```