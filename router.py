def route(question: str):
    q = question.lower()
    wants_news = any(k in q for k in ["news","today","week","month","price","invest","market","company","stock"])
    wants_theory = any(k in q for k in ["why","explain","pe","valuation","risk","fundamental"])
    return {"news": wants_news, "theory": wants_theory}

if __name__=="__main__":
    print(route("Should I invest in steel this month?"))
