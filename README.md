# Portfolio AI

Minimal FastAPI service prepared for Groq integration. Render builds and runs it from `Dockerfile` and checks `/health` before routing traffic.

## Local Development

Requirements: Python 3.14 and Docker. Copy `.env.example` to `.env`, then set `GROQ_API_KEY`.

The AI service does not access GitHub directly. It retrieves a sanitized, six-hour-cached knowledge feed from the Spring Boot backend using `GITHUB_KNOWLEDGE_URL`. The job application master is read from `SKILLS_FILE`, filtered for sensitive and confidential lines, then indexed in memory for retrieval.

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

For production, add `JOB_APPLICATION_MASTER.md` as a Render secret file at `/etc/secrets/JOB_APPLICATION_MASTER.md`. The file must not be committed to a public repository.
