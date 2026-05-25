# Project Title:
DocuMind AI: RAG-based Technical Documentation Assistant

# Main Problem:
Users struggle to find exact answers, from technical documents like manuals, setup guides, and programming documentation.

# Solution:
Upload documents, ask questions, retrieve the most relevant document chunks, generate answers, and show source citations.

# Features:
1.	Multi-PDF Support
2.	Chunking
3.	Embedding’s
4.	Vector DB
5.	Query rewriting / Expansion: when a user types a vague question like “how do I install it?”, the system       rewrites it into a better search query before hitting the vector DB.
6.	Relevance Scoring with Threshold Filtering: don’t just return the top-k chunks blindly. Score them and if nothing crosses a confidence threshold, tell the user “I couldn’t find a reliable answer in your documents” instead of hallucinating.
7.	LLMs for answering
8.	Answer faithfulness check: check whether the answer is actually supported by the retrieved paragraph. Use labels: correct -> answer matches document, partial -> some answer is missing, wrong -> answer not supported, hallucinated -> answer made up
9.	Show Citations: PDF name + page number + highlighted paragraph
10.	Retrieval Evaluation: create around 15 test questions manually from the uploaded PDFs and for each question, check: 
              Question	                 Expected source page	    Retrieved correct source?
      How to install package X?	                Page 5	                       Yes

    Metric: Retrieval Accuracy = correct retrieved answers / total questions
11.	Chat History

# Tech Stack
1.	PDF Text Extraction: use PyMuPDF, gives page numbers for citations
2.	Text Chunking: use LangChain, sentence-aware
3.	Embedding’s: use sentence-transformers, free
4.	Vector DB: use ChromaDB, free, no setup, works offline
5.	LLM for answering: Groq API with llama3-8b, generous free limits
6.	RAG Orchestration: LangChain, clean connection
7.	Chat History: LangChain, built-in
8.	Backend: FastAPI, lightweight
9.	Frontend: Streamlit, fastest for DS projects

# Work Distribution
1.	Ayesha
•	PDF upload handling, text extraction with PyMuPDF, text cleaning
•	Chunking strategy (implement + document the why)
•	Embedding generation and store chunks into vector DB (ChromaDB)
•	Citation metadata storage (page number, doc name, chunk position)
2.	Bisma
•	Query rewriting module
•	Retrieval from vector DB with relevance scoring + threshold filtering
•	Connecting retrieval to LLM (Groq) via LangChain
•	Prompt Engineering (system prompt that tells the LLM to only answer from context, no hallucinations)
3.	Tania
•	Create 15 test questions from PDFs
•	Calculate retrieval accuracy
•	Chat history integration using LangChain memory
•	Multi-PDF session management (tracking which docs are loaded)
•	Citation formatting in the response (doc name, page, paragraph snippet)
4.	Combined Work
•	Streamlit frontend
•	FastAPI backend connection

