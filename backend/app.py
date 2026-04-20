from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

RULES = [
    {
        "patterns": ["açılmıyor", "calismiyor", "çalışmıyor", "hiç açılmıyor", "tepki yok"],
        "message": "Güç hattını kontrol et.",
        "next": "Hiç tepki yok mu?"
    },
    {
        "patterns": ["sigorta", "atıyor", "atiyor", "sigorta atıyor", "sigorta atiyor"],
        "message": "Kısa devre ihtimali var.",
        "next": "Köprü diyot ölçtün mü?"
    },
    {
        "patterns": ["diyot", "yanık", "yanik", "diyot yandı", "diyot yandi"],
        "message": "Diyot hattını kontrol et.",
        "next": "Tek yön iletimi var mı ölçtün mü?"
    },
    {
        "patterns": ["lumos", "hazır mısın", "hazir misin", "burada mısın", "burda mısın"],
        "message": "Hazırım.",
        "next": "Belirtiyi yaz."
    }
]

def normalize(text: str) -> str:
    return text.lower().strip()

def lumos(text: str):
    t = normalize(text)

    for rule in RULES:
        if any(p in t for p in rule["patterns"]):
            return {
                "type": "analysis",
                "message": rule["message"],
                "next": rule["next"]
            }

    return {
        "type": "clarify",
        "message": "Yetersiz veri.",
        "next": "Belirtiyi daha net yaz."
    }

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json or {}
    result = lumos(data.get("text", ""))
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
