# Portfolio AI - Agent Guide

## Current State (2026-08-17)

### Tech Stack
- **Language**: Python 3.14
- **Framework**: FastAPI
- **AI Provider**: Groq (model: `groq/compound`)
- **Knowledge**: GitHub repo data + skills markdown
- **Deploy**: Render auto-deploy on push to main (Docker)

### Architecture
```
GitHub Push (main) → Render builds Docker → Deploys automatically
```

### Key Components
| Component | Location | Purpose |
|-----------|----------|---------|
| Chat Endpoint | `app/main.py:chat()` | Groq completion with portfolio context |
| Knowledge Retriever | `app/knowledge.py` | Fetches/caches GitHub + skills data |
| Health/Time | `app/main.py` | Basic service endpoints |
| CORS | `app/main.py` | Allows zorionten.github.io + localhost |

### API Endpoints
| Endpoint | Method | Auth | Notes |
|----------|--------|------|-------|
| `/health` | GET | - | Returns `chatConfigured: true` if GROQ_API_KEY set |
| `/time` | GET | - | Server time + uptime |
| `/chat` | POST | - | Main AI endpoint, proxied by backend |

### Request/Response Format
```json
// POST /chat request
{
  "message": "string (1-1000 chars)",
  "history": [{"role": "user|assistant", "content": "string"}]  // max 50
}

// Response
{
  "response": "string",
  "sources": ["Verified portfolio facts", "GitHub: repo-name"]
}
```

### Knowledge Sources
1. **Verified Skills Profile**: `JOB_APPLICATION_MASTER.md` (mounted as secret)
2. **GitHub Knowledge**: `https://portfolio-backend-lutt.onrender.com/api/github/knowledge`
   - Cached 6 hours
   - Includes private repo tech inference (no URLs/names exposed)

### Build Commands
```bash
# Local dev
uvicorn app.main:app --reload

# Docker build
docker build -t portfolio-ai .

# Run container
docker run -p 8000:8000 --env-file .env portfolio-ai
```

### Environment Variables (Render)
| Key | Source | Required |
|-----|--------|----------|
| `GROQ_API_KEY` | Dashboard | Yes |
| `GROQ_MODEL` | Dashboard | Yes (`groq/compound`) |
| `GITHUB_KNOWLEDGE_URL` | Blueprint | Yes |
| `SKILLS_FILE` | Blueprint | Yes (`/etc/secrets/JOB_APPLICATION_MASTER.md`) |

### Branching Strategy
```
develop → (PR + review) → staging → (manual promote) → main → (auto-deploy)
```

### Common Issues & Fixes
| Issue | Fix |
|-------|-----|
| 502 on `/chat` | Check Groq model validity (`groq/compound` works) |
| `chatConfigured: false` | Set `GROQ_API_KEY` in Render dashboard |
| Knowledge empty | Verify `GITHUB_KNOWLEDGE_URL` reachable, backend healthy |
| Cold start 20s+ | Free tier spins down; first request triggers wake |

### Model Notes
- **Working**: `groq/compound` (returns actual content)
- **Broken**: `llama-3.x`, `openai/gpt-oss-*` (empty content, only reasoning)
- **Config**: `GROQ_MODEL` env var (default in code: `groq/compound`)

### Deploy Flow
1. Push to `main` triggers Render auto-deploy
2. Render builds Dockerfile, runs container
3. Health check `/health` must pass
4. Service available at https://portfolio-ai-dla4.onrender.com

### Render Service
- **URL**: https://portfolio-ai-dla4.onrender.com
- **Dashboard**: https://dashboard.render.com/web/srv-d9vajdbl550s7384tjig
- **Runtime**: docker (builds from GitHub repo)
- **Auto-deploy**: Enabled on commit to main
- **Region**: Singapore (free tier)

### Files to Watch
- `app/main.py` - Chat logic, system prompt, model config
- `app/knowledge.py` - Retrieval, chunking, ranking
- `Dockerfile` - Python version, dependencies
- `.env` - Local dev config (not committed)