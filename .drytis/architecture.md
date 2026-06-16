# Architecture

## Directory Structure
```
/workspace/
├── app.py                    # FastAPI web server (entry point)
├── coordinator_graph.py      # LangGraph orchestration
├── router.py                 # Question router
├── news_agent.py             # News fetching agent
├── rag_agent.py              # RAG retrieval agent
├── finbert_agent.py          # Sentiment analysis agent
├── llm_merge_gemini.py       # Gemini merge/summary
├── requirements.txt          # Root dependencies
├── templates/
│   └── index.html            # Chat UI
├── mcp/
│   ├── fmp_server.py         # FMP MCP server (unchanged)
│   ├── alpaca_server.py      # Alpaca MCP server (unchanged)
│   ├── main_host.py          # CLI MCP host (unchanged)
│   └── requirements.txt      # MCP deps
├── corpus_theory/            # RAG knowledge corpus
├── chroma_rag/               # ChromaDB storage (runtime)
└── .drytis/                  # Blueprints + specs
```

## Data Flow
```
Browser → POST /ask → FastAPI → coordinator_graph (LangGraph)
  → router decides path (news / rag / both)
  → agents execute (news fetch, sentiment, RAG retrieval)
  → gemini merges results → final answer → JSON response → Browser
```

## Routing
- `GET /` → Chat UI (index.html)
- `POST /api/ask` → Financial question → recommendation
- `GET /api/health` → Health check
- `GET /api/agents` → List available agents and their status
```
```
