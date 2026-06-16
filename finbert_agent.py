import logging

logger = logging.getLogger("finbert_agent")

FINBERT_MODEL = "ProsusAI/finbert"

# Lazy-loaded singletons
_tokenizer = None
_model = None
_nltk_ready = False


def _ensure_nltk():
    """Download required NLTK data (once)."""
    global _nltk_ready
    if not _nltk_ready:
        import nltk
        nltk.download("punkt", quiet=True)
        nltk.download("punkt_tab", quiet=True)
        _nltk_ready = True


def get_device():
    """Return CUDA device if available, else CPU."""
    import torch
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def get_model():
    """Lazily load FinBERT tokenizer + model (singleton)."""
    global _tokenizer, _model
    if _model is None or _tokenizer is None:
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        logger.info("Loading FinBERT model '%s' ...", FINBERT_MODEL)
        _tokenizer = AutoTokenizer.from_pretrained(FINBERT_MODEL)
        _model = AutoModelForSequenceClassification.from_pretrained(FINBERT_MODEL)
        _model.to(get_device())
        _model.eval()
    return _tokenizer, _model


def split_sentences(text: str):
    """Tokenize text into sentences using NLTK."""
    _ensure_nltk()
    import nltk
    sents = nltk.sent_tokenize(text)
    return [s.strip() for s in sents if s.strip()]


def classify_sentence(sentence: str):
    """Classify a single sentence's financial sentiment."""
    import torch
    tokenizer, model = get_model()
    device = get_device()

    inputs = tokenizer(sentence, return_tensors="pt", truncation=True).to(device)
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.softmax(logits, dim=-1).cpu().numpy().tolist()[0]
    p_neg, p_neu, p_pos = probs
    label = ["negative", "neutral", "positive"][int(torch.argmax(logits, 1).item())]
    return {
        "sentence": sentence,
        "p_neg": p_neg,
        "p_neu": p_neu,
        "p_pos": p_pos,
        "label": label,
        "score": p_pos - p_neg,
    }


def analyze_sentiment(text: str):
    """Analyze sentiment of an article/block of text.

    Returns dict with:
        - sentences: list of per-sentence results
        - article_score: average sentiment score (-1 to 1)
        - pos_frac / neg_frac / neutral_frac: fraction of sentences
    """
    sentences = split_sentences(text)
    if not sentences:
        return {
            "sentences": [],
            "article_score": 0.0,
            "pos_frac": 0.0,
            "neg_frac": 0.0,
            "neutral_frac": 0.0,
        }

    results = [classify_sentence(s) for s in sentences]
    avg_score = sum(r["score"] for r in results) / len(results)
    pos = sum(1 for r in results if r["label"] == "positive")
    neg = sum(1 for r in results if r["label"] == "negative")
    neu = sum(1 for r in results if r["label"] == "neutral")
    total = len(results)
    return {
        "sentences": results,
        "article_score": round(avg_score, 4),
        "pos_frac": round(pos / total, 4),
        "neg_frac": round(neg / total, 4),
        "neutral_frac": round(neu / total, 4),
    }


if __name__ == "__main__":
    text = "Steel demand grew. However, raw materials are getting expensive."
    print(analyze_sentiment(text))
