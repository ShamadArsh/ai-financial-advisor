import nltk
nltk.download('punkt')
nltk.download('punkt_tab')

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

FINBERT_MODEL = "ProsusAI/finbert"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

tokenizer = AutoTokenizer.from_pretrained(FINBERT_MODEL)
model = AutoModelForSequenceClassification.from_pretrained(FINBERT_MODEL)
model.to(device)
model.eval()

def split_sentences(text: str):
    sents = nltk.sent_tokenize(text)
    return [s.strip() for s in sents if s.strip()]

def classify_sentence(sentence: str):
    inputs = tokenizer(sentence, return_tensors="pt", truncation=True).to(device)
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.softmax(logits, dim=-1).cpu().numpy().tolist()[0]
    p_neg, p_neu, p_pos = probs
    label = ["negative","neutral","positive"][int(torch.argmax(logits,1).item())]
    return {
        "sentence": sentence,
        "p_neg": p_neg,
        "p_neu": p_neu,
        "p_pos": p_pos,
        "label": label,
        "score": p_pos - p_neg
    }

def analyze_sentiment(text: str):
    sentences = split_sentences(text)
    results = [classify_sentence(s) for s in sentences]
    avg_score = sum(r["score"] for r in results)/len(results)
    pos = sum(1 for r in results if r["label"]=="positive")
    neg = sum(1 for r in results if r["label"]=="negative")
    neu = sum(1 for r in results if r["label"]=="neutral")
    total = len(results)
    return {
        "sentences": results,
        "article_score": avg_score,
        "pos_frac": pos/total,
        "neg_frac": neg/total,
        "neutral_frac": neu/total
    }

if __name__=="__main__":
    text = "Steel demand grew. However, raw materials are getting expensive."
    print(analyze_sentiment(text))
