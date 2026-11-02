from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

last_topic = None

def normalize(text: str) -> str:
    return text.lower().strip()

def detect_topic(t: str):
    if any(x in t for x in ["açılmıyor", "calismiyor", "çalışmıyor", "tepki yok", "hiç açılmıyor"]):
        return "power"
    if any(x in t for x in ["sigorta", "atıyor", "atiyor", "sigorta atıyor", "sigorta atiyor"]):
        return "short"
    if any(x in t for x in ["diyot", "yanık", "yanik", "diyot yandı", "diyot yandi"]):
        return "diode"
    if any(x in t for x in ["lumos", "hazır mısın", "hazir misin", "burada mısın", "burda mısın"]):
        return "lumos"
    return None

def lumos(text: str, state=None):
    global last_topic

    t = normalize(text)
    topic = detect_topic(t)

    if topic is not None and topic != last_topic:
        state = None

    last_topic = topic

    if not state:
        if topic == "power":
            return {
                "message": "Güç hattını kontrol et.",
                "next": "Hiç tepki var mı?",
                "state": "power_check"
            }

        if topic == "short":
            return {
                "message": "Kısa devre ihtimali var.",
                "next": "Cihazı açar açmaz mı atıyor, yoksa biraz çalıştıktan sonra mı?",
                "state": "short_check"
            }

        if topic == "diode":
            return {
                "message": "Diyot hattını kontrol et.",
                "next": "Tek yön ölçtün mü?",
                "state": "diode_check"
            }

        if topic == "lumos":
            return {
                "message": "Hazırım.",
                "next": "Belirtiyi yaz.",
                "state": None
            }

        return {
            "message": "Yetersiz veri.",
            "next": "Belirtiyi net yaz.",
            "state": None
        }

    if state == "power_check":
        if "yok" in t:
            return {
                "message": "Primer tarafı kontrol et.",
                "next": "Sigorta sağlam mı?",
                "state": "power_detail"
            }
        return {
            "message": "Devam et.",
            "next": "Sigorta durumunu yaz.",
            "state": "power_detail"
        }

    if state == "power_detail":
        return {
            "message": "Güç yolunu daraltıyoruz.",
            "next": "Primerden sonra hangi noktada voltaj düşüyor?",
            "state": None
        }

    if state == "short_check":
        if "hemen" in t:
            return {
                "message": "Direkt kısa devre var.",
                "next": "Köprü diyotu ölç.",
                "state": None
            }
        return {
            "message": "Yük altında atıyor.",
            "next": "Sekonderi kontrol et.",
            "state": None
        }

    if state == "diode_check":
        if "yok" in t:
            return {
                "message": "Diyot arızalı.",
                "next": "Değiştir.",
                "state": None
            }
        return {
            "message": "Diyot sağlam olabilir.",
            "next": "Bağlı hattı kontrol et.",
            "state": None
        }

    return {
        "message": "Anlamadım.",
        "next": "Tekrar yaz.",
        "state": None
    }

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json or {}
    text = data.get("text", "")
    state = data.get("state", None)
    result = lumos(text, state)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
