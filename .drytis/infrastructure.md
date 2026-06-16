# Infrastructure

## Proxy Routes
- Caddy reverse proxy at `/` → port 8000 (FastAPI/Uvicorn)

## Background Services
- `app-server`: Uvicorn serving FastAPI on port 8000

## Environment Variables
All stored via backend env_key tool, written to `/workspace/.env`:
- NEWSAPI_KEY_ORG — NewsAPI.org key
- FMP_API_KEY — FinancialModelingPrep key
- ALPACA_API_KEY — Alpaca API key
- ALPACA_SECRET_KEY — Alpaca secret
- GROQ_API_KEY — Groq API key
- GOOGLE_API_KEY — Google/Gemini API key

## Ports
- 8000: FastAPI (Uvicorn)
```
```
