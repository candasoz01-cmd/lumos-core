from core.lumos import Lumos
from context.context import Context
from policy.offline_engine import OfflineEngineV1

def run():
    lumos = Lumos(mode="offline", engine=OfflineEngineV1())
    ctx = Context(message="selam", online=False, confidence=1.0, user_is_child=False)
    out = lumos.respond(ctx)
    assert out and "Şunu duyuyorum" in out, f"Beklenmeyen çıktı: {out}"
    print("OK: offline")

if __name__ == "__main__":
    run()
