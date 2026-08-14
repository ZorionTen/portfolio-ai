# Portfolio AI

Minimal FastAPI service prepared for Groq integration. Render builds and runs it from `Dockerfile` and checks `/health` before routing traffic.

## Local Development

Requirements: Python 3.14 and Docker.

```bash
python -m venv .venv
source .venv/bin/activate
pip install --requirement requirements-dev.txt
uvicorn app.main:app --reload
```

The service listens on `http://localhost:8000`. Run its tests with:

```bash
python -m pytest
```

## Docker

```bash
docker build -t portfolio-ai .
docker run --rm -p 8000:8000 -e GROQ_API_KEY portfolio-ai
```

## Render

Deployment is managed by the Blueprint in `ZorionTen/portfolio-backend`. Render prompts for `GROQ_API_KEY` during initial setup and automatically deploys `main` after CI succeeds.
