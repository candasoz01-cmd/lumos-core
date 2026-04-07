import json

from kando_bridge.server import _resolve_task_routing, extract_chat_task_file_ref
from kando_runtime.bridge_intent import classify_bridge_message_intent


def test_classify_intent_normal_chat():
    assert classify_bridge_message_intent("merhaba") == "chat"


def test_classify_intent_with_file_and_action():
    assert classify_bridge_message_intent("README.md dosyasını düzelt") == "task"


def test_classify_intent_mixed():
    assert classify_bridge_message_intent("şu fonksiyonu değiştir foo.py içinde") == "task"


def test_classify_intent_action_plus_object_without_path():
    """Bridge task sinyali lumos_gate yapısı ile hizalı: yol yokken eylem+nesne yeter."""
    assert classify_bridge_message_intent("fonksiyonu güncelle") == "task"


def test_classify_intent_action_object_hardened():
    """Çözünürlük/fiyat parçaları task kararını düşürmez; soru cümlesi chat kalır."""
    assert classify_bridge_message_intent("video üret") == "task"
    assert classify_bridge_message_intent("720p video üret") == "task"
    assert classify_bridge_message_intent("video üret 0.10p") == "task"
    assert classify_bridge_message_intent("kısa video oluştur") == "task"
    assert classify_bridge_message_intent("tüm dosyaları sil") == "task"
    assert classify_bridge_message_intent("nasıl video üretirim") == "chat"


def test_extract_file_ref():
    assert extract_chat_task_file_ref("README.md dosyasını özetle") == "README.md"
    assert extract_chat_task_file_ref("src/foo.py değiştir") == "src/foo.py"
    assert extract_chat_task_file_ref("selam") is None


def test_resolve_task_json_strips_dosya_yolu_prefix():
    raw = json.dumps(
        {"file": "Dosya yolu: README.md", "task": "Bu dosyayı sil"},
        ensure_ascii=False,
    ).encode()
    err, mode, payload, _ = _resolve_task_routing("application/json", raw)
    assert err is None
    assert mode == "direct_patch"
    assert payload.startswith("TARGET: README.md\n")


def test_resolve_task_json_junk_file_falls_back_to_task_path():
    raw = json.dumps(
        {"file": "Görev (sistemde işlem)", "task": "README.md'yi sil."},
        ensure_ascii=False,
    ).encode()
    err, mode, payload, _ = _resolve_task_routing("application/json", raw)
    assert err is None
    assert mode == "direct_patch"
    assert payload.startswith("TARGET: README.md\n")
