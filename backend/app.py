from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def lumos(text):
    t = text.lower()

    if "açılmıyor" in t:
        return {
            "type": "analysis",
            "message": "Giriş yok. Güç hattına bak.",
            "next": "Sigorta sağlam mı?"
        }

    if "sigorta" in t:
        return {
            "type": "analysis",
            "message": "Kısa devre ihtimali var.",
            "next": "Köprü diyotu ölçtün mü?"
        }

    return {
        "type": "clarify",
        "message": "Yetersiz veri.",
        "next": "Ne oluyor? Belirtiyi net yaz."
    }

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    result = lumos(data.get("text", ""))
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
