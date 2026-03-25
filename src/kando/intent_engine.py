from kando.intents_tr import INTENTS
from kando.llm import normalize


class IntentEngine:
    def __init__(self):
        self.intents = INTENTS

    def match(self, text: str):
        t = normalize(text)

        if t.startswith("repo:"):
            return "repo"
        if t == "repo":
            return "repo"

        scores = {}

        def add_score(intent, val):
            scores[intent] = scores.get(intent, 0) + val

        # 1. prefix
        for intent, patterns in self.intents.items():
            for p in patterns:
                if t.startswith(normalize(p)):
                    add_score(intent, 3)

        # 2. substring
        for intent, patterns in self.intents.items():
            for p in patterns:
                if normalize(p) in t:
                    add_score(intent, 2)

        # 3. fuzzy
        words = t.split()
        for intent, patterns in self.intents.items():
            for p in patterns:
                pn = normalize(p)
                for w in words:
                    if abs(len(w) - len(pn)) <= 2 and w[:3] == pn[:3]:
                        add_score(intent, 1)

        if scores:
            # skor filtresi ama input sırasını koru
            result = []
            for intent, score in scores.items():
                if score >= 1:
                    result.append(intent)

            if result:
                return result

        return "unknown"


engine = IntentEngine()
