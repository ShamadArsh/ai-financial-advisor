import os
import logging

logger = logging.getLogger("llm_merge_gemini")

_llm_instance = None


def _get_llm():
    """Create and cache the Gemini LLM instance (singleton)."""
    global _llm_instance
    if _llm_instance is None:
        from langchain_google_genai import ChatGoogleGenerativeAI
        _llm_instance = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.2,
        )
    return _llm_instance


def llm_merge_gemini(
    question: str,
    sentiment: dict,
    news_items: list,
    rag_hits: list,
    conversation_history: list | None = None,
) -> str:
    """Merge all agent outputs into a final recommendation using Gemini.

    Args:
        conversation_history: List of {"role": "user"|"assistant", "content": "..."} dicts
                              from prior turns. Used to resolve follow-up questions.
    """
    llm = _get_llm()

    # Keep only essential fields to avoid huge prompt length
    news_summary = "\n".join(
        [
            f"- {n.get('title', 'N/A')} ({n.get('source', 'N/A')})"
            for n in (news_items or [])[:4]
        ]
    )

    rag_summary = "\n".join(
        [
            f"- {h.get('text', '')[:120]}..."
            for h in (rag_hits or [])[:3]
        ]
    )

    sent_score = sentiment.get("article_score") if sentiment else None
    pos = sentiment.get("pos_frac") if sentiment else None
    neg = sentiment.get("neg_frac") if sentiment else None

    # Build conversation context section
    history_block = ""
    if conversation_history:
        history_lines = []
        for msg in conversation_history[-8:]:  # Last 8 messages max
            role = msg.get("role", "")
            content = msg.get("content", "")[:200]
            if role == "user":
                history_lines.append(f"  User: {content}")
            elif role == "assistant":
                history_lines.append(f"  Advisor: {content}")
        if history_lines:
            history_block = f"""
PREVIOUS CONVERSATION (use this context for follow-up questions):
{chr(10).join(history_lines)}
"""

    human_prompt = f"""
You are a financial reasoning assistant. You are having a conversation with the user.
If the user asks a follow-up question (like "what about Tesla?" or "which is better?"),
use the conversation history to understand what they're referring to.
{history_block}
USER QUESTION:
{question}

MARKET SENTIMENT:
- Sentiment score: {sent_score}
- Positive: {pos}
- Negative: {neg}

LATEST NEWS (top 4):
{news_summary}

THEORY EVIDENCE:
{rag_summary}

TASK:
Write 3 short bullet points:
1. A concise recommendation (1-2 sentences)
2. One supporting fact from the news or theory
3. One short risk to consider

Keep it direct, analytical, and avoid any legal disclaimers.
If the user is asking a comparison or follow-up, reference the previous topic directly.
"""

    try:
        resp = llm.invoke(human_prompt)
        if hasattr(resp, "content") and resp.content:
            return resp.content.strip()
        return str(resp)
    except Exception as e:
        logger.error("Gemini merge failed: %s", e)
        return f"[Gemini Merge Error] {e}"
