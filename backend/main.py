from fastapi import FastAPI

app = FastAPI(
    title="HealthScope AI",
    version="1.0.0"
)

@app.get("/")
def root():
    return {
        "message": "HealthScope AI API Running"
    }