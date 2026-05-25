from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "DocuMind AI backend is running"}