from fastapi import FastAPI

app = FastAPI(title="Portfolio AI", version="0.1.0")


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "portfolio-ai", "status": "ready"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
