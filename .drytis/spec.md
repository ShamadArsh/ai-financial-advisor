# Financial AI Advisor — Spec

## Overview
AI-powered financial advisory app with 3 specialized agents + MCP integration, wrapped in a FastAPI web application with a chat UI.

## Tech Stack
- **Backend:** Python 3, FastAPI, Uvicorn
- **AI/ML:** LangGraph, Transformers (FinBERT), SentenceTransformers, ChromaDB
- **LLM:** Google Gemini (via langchain-google-genai), Groq
- **External APIs:** NewsAPI.org, FinancialModelingPrep, Alpaca (paper trading)
- **MCP:** Model Context Protocol servers (FMP + Alpaca)
- **Frontend:** HTML/CSS/JS (vanilla, no framework)

## Key Decisions
- Models (FinBERT, SentenceTransformers) loaded lazily to avoid crashes on import
- LLM instances cached as singletons
- API keys stored as environment variables (never hardcoded)
- Graceful degradation when keys are missing
- MCP servers run as subprocesses spawned on-demand
