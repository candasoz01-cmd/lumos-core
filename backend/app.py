from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def lumos(t):
    t = t.lower()

    if any(x in t for x in ["açılmıyor", "çalışmıyor"]):
        return {
            "type": "analysis",
            "message": "Güç hattını kontrol et.",
            "next": "Hiç tepki yok mu?"
        }

    if any(x in t for x in ["sigorta", "atıyor"]):
        return {
            "type": "analysis",
            "message": "Kısa devre ihtimali var.",
            "next": "Köprü diyot ölçtün mü?"
        }

    if any(x in t for x in ["diyot", "yanık"]):
        return {
            "type": "analysis",
            "message": "Diyot hattını kontrol et.",
            "next": "Tek yön iletimi var mı ölçtün mü?"
        }

    return {
        "type": "clarify",
        "message": "Yetersiz veri.",
        "next": "Belirtiyi daha net yaz."
    }

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    result = lumos(data.get("text", ""))
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
