from fastapi import FastAPI

app = FastAPI(title="CBSE Tutor API")

@app.get("/")
def home():
    return {"message": "CBSE Tutor API is running"}