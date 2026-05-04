# from langgraph.graph import StateGraph, START, END
# from typing import TypedDict, List, Dict
# from pprint import pprint

# from finbert_agent import analyze_sentiment
# from rag_agent import retrieve
# from news_agent import get_news
# from router import route

# class GraphState(TypedDict):
#     question: str
#     news: List[Dict]
#     sentiment: Dict
#     documents: List[Dict]
#     answer: str

# def node_route(s:GraphState):
#     r = route(s["question"])
#     if r["news"] and not r["theory"]:
#         return {"next":"news_and_sentiment"}
#     if r["theory"] and not r["news"]:
#         return {"next":"rag_only"}
#     if r["news"] and r["theory"]:
#         return {"next":"news_and_rag"}
#     return {"next":"rag_only"}

# def node_news_and_sentiment(s):
#     news_items = get_news(s["question"])
#     combined = "\n".join([n.get("content","") or n.get("title","") for n in news_items])
#     sentiment = analyze_sentiment(combined)
#     return {"news":news_items, "sentiment":sentiment}

# def node_rag_only(s):
#     docs = retrieve(s["question"])
#     return {"documents":docs}

# def node_news_and_rag(s):
#     news_items = get_news(s["question"])
#     combined = "\n".join([n.get("content","") or n.get("title","") for n in news_items])
#     sentiment = analyze_sentiment(combined)
#     docs = retrieve(s["question"])
#     return {"news":news_items, "sentiment":sentiment, "documents":docs}

# def node_merge(s):
#     q=s["question"]
#     sent=s.get("sentiment",{})
#     news=s.get("news",[])
#     docs=s.get("documents",[])
#     answer = f"Question: {q}\n\nSentiment: {sent}\n\nTheory: {docs[:2]}\n\nNews: {[n['title'] for n in news[:3]]}"
#     return {"answer":answer}

# workflow = StateGraph(GraphState)
# workflow.add_node("route", node_route)
# workflow.add_node("news_and_sentiment", node_news_and_sentiment)
# workflow.add_node("rag_only", node_rag_only)
# workflow.add_node("news_and_rag", node_news_and_rag)
# workflow.add_node("merge", node_merge)

# workflow.add_conditional_edges(START, lambda s: node_route(s)["next"],{
#     "news_and_sentiment":"news_and_sentiment",
#     "rag_only":"rag_only",
#     "news_and_rag":"news_and_rag"
# })
# workflow.add_edge("news_and_sentiment","merge")
# workflow.add_edge("rag_only","merge")
# workflow.add_edge("news_and_rag","merge")
# workflow.add_edge("merge",END)

# app = workflow.compile()

# if __name__=="__main__":
#     out=None
#     for o in app.stream({"question":"Should I invest in steel this month?"}):
#         pprint(o)
#         out=o
#     print("\nFINAL ANSWER:\n", out["merge"]["answer"])


from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Dict, Any
from pprint import pprint

from finbert_agent import analyze_sentiment
from rag_agent import retrieve
from news_agent import get_industry_news
from router import route
from llm_merge_gemini import llm_merge_gemini


# -------------------------------
# Graph State
# -------------------------------
class GraphState(TypedDict):
    question: str
    industry: str | None
    news_items: List[Dict] | None
    sentiment: Dict | None
    rag_hits: List[Dict] | None
    final: Dict | None

# -------------------------------
# Nodes
# -------------------------------
def route_node(state: GraphState) -> str:
    q = state["question"]
    routing = route(q)

    industry = state.get("industry")
    if industry:
        return "news_and_rag"

    if routing["news"] and not routing["theory"]:
        return "news_and_sentiment"

    if routing["theory"] and not routing["news"]:
        return "rag_only"

    if routing["theory"] and routing["news"]:
        return "news_and_rag"

    return "rag_only"


def news_and_sentiment_node(state: GraphState):
    q = state["question"]
    industry = state.get("industry") or q

    news = get_industry_news(industry, max_items=8)
    combined = "\n".join([(n.get("content") or n.get("title") or "") for n in news])
    sentiment = analyze_sentiment(combined)

    return {"news_items": news, "sentiment": sentiment}


def rag_only_node(state: GraphState):
    q = state["question"]
    hits = retrieve(q)
    return {"rag_hits": hits}


def news_and_rag_node(state: GraphState):
    q = state["question"]
    industry = state.get("industry") or q

    news = get_industry_news(industry, max_items=8)
    combined = "\n".join([(n.get("content") or n.get("title") or "") for n in news])
    sentiment = analyze_sentiment(combined)
    hits = retrieve(q)

    return {"news_items": news, "sentiment": sentiment, "rag_hits": hits}


# def merge_node(state: GraphState):
#     q = state["question"]
#     news = state.get("news_items") or []
#     sentiment = state.get("sentiment") or {}
#     rag_hits = state.get("rag_hits") or []

#     answer = f"Q: {q}\n\n"
#     answer += f"Sentiment score: {sentiment.get('article_score', None)}\n"
#     answer += f"Top news: {[n.get('title') for n in news[:3]]}\n"
#     answer += f"Top theory excerpts: {[h.get('text')[:80] for h in rag_hits[:2]]}\n"

#     final = {
#         "question": q,
#         "answer": answer,
#         "sentiment": sentiment,
#         "news_items": news,
#         "rag_hits": rag_hits
#     }

#     return {"final": final}
def merge_node(state: GraphState):
    q = state["question"]
    news = state.get("news_items") or []
    sentiment = state.get("sentiment") or {}
    rag_hits = state.get("rag_hits") or []

    try:
        answer = llm_merge_gemini(q, sentiment, news, rag_hits)
    except Exception as e:
        print("Gemini merge failed:", e)
        answer = f"Q: {q}\nSentiment score: {sentiment.get('article_score')}\nNews: {[n.get('title') for n in news[:3]]}"

    final = {
        "question": q,
        "answer": answer,
        "sentiment": sentiment,
        "news_items": news,
        "rag_hits": rag_hits
    }

    return {"final": final}


# -------------------------------
# Build Graph
# -------------------------------
workflow = StateGraph(GraphState)

workflow.add_node("news_and_sentiment", news_and_sentiment_node)
workflow.add_node("rag_only", rag_only_node)
workflow.add_node("news_and_rag", news_and_rag_node)
workflow.add_node("merge", merge_node)

workflow.add_conditional_edges(
    START,
    route_node,
    {
        "news_and_sentiment": "news_and_sentiment",
        "rag_only": "rag_only",
        "news_and_rag": "news_and_rag"
    }
)

workflow.add_edge("news_and_sentiment", "merge")
workflow.add_edge("rag_only", "merge")
workflow.add_edge("news_and_rag", "merge")
workflow.add_edge("merge", END)

app = workflow.compile()

# -------------------------------
# Test
# -------------------------------
if __name__ == "__main__":
    final_state = app.invoke({
        "question": "Should I invest in steel this month?",
        "industry": "steel"
    })

    print("\n=========== FINAL STATE ===========")
    pprint(final_state["final"])
