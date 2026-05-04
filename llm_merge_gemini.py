# llm_merge_gemini.py
import os
from langchain_google_genai import ChatGoogleGenerativeAI

def llm_merge_gemini(question: str, sentiment: dict, news_items: list, rag_hits: list) -> str:

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.2,
        # max_output_tokens=300
    )

    # Keep only essential fields to avoid huge prompt length
    news_summary = "\n".join([
        f"- {n.get('title')} ({n.get('source')})"
        for n in news_items[:4]
    ])

    rag_summary = "\n".join([
        f"- {h.get('text')[:120]}..."
        for h in rag_hits[:3]
    ])

    sent_score = sentiment.get("article_score")
    pos = sentiment.get("pos_frac")
    neg = sentiment.get("neg_frac")

    # Short and clean prompt
    human_prompt = f"""
You are a financial reasoning assistant.

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
1. A concise recommendation (1–2 sentences)
2. One supporting fact from the news or theory
3. One short risk to consider

Keep it direct, analytical, and avoid any legal disclaimers.
"""

    try:
        resp = llm.invoke(human_prompt)

        if hasattr(resp, "content") and resp.content:
            return resp.content.strip()

        # ultimate fallback
        return str(resp)
        
    except Exception as e:
        return f"[Gemini Merge Error] {e}"
# # llm_merge_gemini.py
# # llm_merge_gemini.py
# from langchain_google_genai import ChatGoogleGenerativeAI

# def llm_merge_gemini(question: str, sentiment: dict, news_items: list, rag_hits: list):

#     llm = ChatGoogleGenerativeAI(
#         model="gemini-2.5-flash",
#         temperature=0.2,
#         max_tokens=300
#     )

#     # Convert inputs to simple readable text
#     sent_score = sentiment.get("article_score")
#     pos = sentiment.get("pos_frac")
#     neg = sentiment.get("neg_frac")

#     news_lines = ", ".join([n.get("title") for n in news_items[:3]])
#     theory_lines = " ".join([h.get("text")[:120] for h in rag_hits[:2]])

#     # SIMPLE PLAIN PROMPT (NO SECTIONS, NO HEADERS)
#     prompt = (
#         f"The question is: {question}. "
#         f"The sentiment score is {sent_score}, with positive={pos} and negative={neg}. "
#         f"Recent news headlines include: {news_lines}. "
#         f"Theory notes: {theory_lines}. "
#         "Given this context, summarize the outlook in 3 short bullet points: "
#         "(1) recommendation, (2) evidence, (3) risk."
#     )

#     try:
#         resp = llm.invoke(prompt)
#         # print(resp)
#         txt = resp.content.strip()
#         if txt:
#             return txt
#         return "No response generated."
#     except Exception as e:
#         return f"[Error during merge] {e}"
