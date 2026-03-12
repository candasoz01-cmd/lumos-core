"""Görev motoru, yetki profili ve görev kaydı testleri."""
import tempfile

from task_engine import (
    TaskStore,
    TaskEngine,
    PROFILE_GUVENLI_YURUT,
    PROFILE_RAPOR,
    PROFILE_KISITLI_OTONOM,
)
from task_engine.profiles import (
    is_allowed_for_profile,
    STEP_TYPE_ANALYZE,
    STEP_TYPE_READ,
    STEP_TYPE_PLAN,
    STEP_TYPE_SAFE_LOCAL,
    STEP_TYPE_WRITE_LOCAL,
    STEP_TYPE_EXTERNAL,
    STEP_TYPE_CRITICAL,
)
from task_engine.engine import TaskStep


def test_task_store_create_and_list():

    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Test görev", "not sistemini kontrol et", PROFILE_GUVENLI_YURUT)
        assert t.task_id == 1
        assert t.status == "bekliyor"
        assert len(t.steps) >= 1
        all_tasks = store.list_all()
        assert len(all_tasks) == 1
        assert store.get(1).title == "Test görev"


def test_task_engine_run():
    """guvenli_yurut + not kontrol: base_dir verilirse gerçek okuma yapılır; en az bir doğrulama varsa kismi veya tamamlandi."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Kontrol", "not sistemini kontrol et ve özet ver", PROFILE_GUVENLI_YURUT)
        engine = TaskEngine(store, PROFILE_GUVENLI_YURUT, True, base_dir=d)
        ok, msg = engine.run_task(t.task_id)
        assert ok is True
        t2 = store.get(t.task_id)
        assert t2.status in ("tamamlandi", "kismi"), "doğrulama yapıldığında tamamlandi veya kismi"
        assert t2.verified_count >= 1
        assert t2.status != "dogrulanamadi"


def test_permission_profiles():
    from task_engine import ALL_PROFILES, get_profile_display_name

    assert PROFILE_RAPOR in ALL_PROFILES
    assert PROFILE_GUVENLI_YURUT in ALL_PROFILES
    assert "rapor" in get_profile_display_name(PROFILE_RAPOR)
    assert "güvenli" in get_profile_display_name(PROFILE_GUVENLI_YURUT)


def test_security_boundary():
    from task_engine.profiles import SECURITY_BOUNDARY_DESCRIPTION, SECURITY_NEVER_AUTO

    assert "kalıcı silme" in SECURITY_BOUNDARY_DESCRIPTION or "silme" in SECURITY_BOUNDARY_DESCRIPTION
    assert "permanent_delete" in SECURITY_NEVER_AUTO


# --- Yetki profili: is_allowed_for_profile matrisi ---


def test_profile_rapor_only_analyze_read_plan():
    """rapor: sadece analyze, read, plan; safe_local ve write_local asla."""
    for step_type in (STEP_TYPE_ANALYZE, STEP_TYPE_READ, STEP_TYPE_PLAN):
        assert is_allowed_for_profile(PROFILE_RAPOR, step_type, False) is True
        assert is_allowed_for_profile(PROFILE_RAPOR, step_type, True) is True
    for step_type in (STEP_TYPE_SAFE_LOCAL, STEP_TYPE_WRITE_LOCAL, STEP_TYPE_EXTERNAL, STEP_TYPE_CRITICAL):
        assert is_allowed_for_profile(PROFILE_RAPOR, step_type, False) is False
        assert is_allowed_for_profile(PROFILE_RAPOR, step_type, True) is False


def test_profile_guvenli_yurut_allows_safe_local_not_write_local():
    """guvenli_yurut: analyze, read, plan, safe_local; write_local asla (genel onay fark etmez)."""
    for step_type in (STEP_TYPE_ANALYZE, STEP_TYPE_READ, STEP_TYPE_PLAN, STEP_TYPE_SAFE_LOCAL):
        assert is_allowed_for_profile(PROFILE_GUVENLI_YURUT, step_type, False) is True
        assert is_allowed_for_profile(PROFILE_GUVENLI_YURUT, step_type, True) is True
    assert is_allowed_for_profile(PROFILE_GUVENLI_YURUT, STEP_TYPE_WRITE_LOCAL, False) is False
    assert is_allowed_for_profile(PROFILE_GUVENLI_YURUT, STEP_TYPE_WRITE_LOCAL, True) is False
    assert is_allowed_for_profile(PROFILE_GUVENLI_YURUT, STEP_TYPE_CRITICAL, True) is False
    assert is_allowed_for_profile(PROFILE_GUVENLI_YURUT, STEP_TYPE_EXTERNAL, True) is False


def test_profile_kisitli_otonom_genel_onay_kapali():
    """kisitli_otonom, genel onay kapalı: sadece analyze, read, plan."""
    for step_type in (STEP_TYPE_ANALYZE, STEP_TYPE_READ, STEP_TYPE_PLAN):
        assert is_allowed_for_profile(PROFILE_KISITLI_OTONOM, step_type, False) is True
    assert is_allowed_for_profile(PROFILE_KISITLI_OTONOM, STEP_TYPE_SAFE_LOCAL, False) is False
    assert is_allowed_for_profile(PROFILE_KISITLI_OTONOM, STEP_TYPE_WRITE_LOCAL, False) is False


def test_profile_kisitli_otonom_genel_onay_acik():
    """kisitli_otonom, genel onay açık: safe_local ve write_local da izinli; critical/external asla."""
    for step_type in (STEP_TYPE_ANALYZE, STEP_TYPE_READ, STEP_TYPE_PLAN, STEP_TYPE_SAFE_LOCAL, STEP_TYPE_WRITE_LOCAL):
        assert is_allowed_for_profile(PROFILE_KISITLI_OTONOM, step_type, True) is True
    assert is_allowed_for_profile(PROFILE_KISITLI_OTONOM, STEP_TYPE_CRITICAL, True) is False
    assert is_allowed_for_profile(PROFILE_KISITLI_OTONOM, STEP_TYPE_EXTERNAL, True) is False


def test_engine_rapor_blocks_safe_local_step():
    """rapor profilde safe_local adım çalıştırılırsa görev durur, adım izin dışı işaretlenir."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("X", "not kontrol", PROFILE_RAPOR)
        t.steps = [TaskStep("Yerel güvenli iş", kind=STEP_TYPE_SAFE_LOCAL)]
        store.update(t)
        engine = TaskEngine(store, PROFILE_RAPOR, True)
        ok, msg = engine.run_task(t.task_id)
        assert ok is False
        assert "izin" in msg.lower() or "yetki" in msg.lower() or "dışı" in msg.lower()
        t2 = store.get(t.task_id)
        assert t2.status == "durdu"
        assert any(s.status == "durdu" and s.error for s in t2.steps)


def test_engine_kisitli_otonom_no_approval_blocks_write_local():
    """kisitli_otonom + genel onay kapalı: write_local adım çalışmaz."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Yaz", "özet ver", PROFILE_KISITLI_OTONOM)
        t.steps = [TaskStep("Dosyaya yaz", kind=STEP_TYPE_WRITE_LOCAL)]
        store.update(t)
        engine = TaskEngine(store, PROFILE_KISITLI_OTONOM, general_approval=False)
        ok, msg = engine.run_task(t.task_id)
        assert ok is False
        assert "izin" in msg.lower() or "yetki" in msg.lower() or "dışı" in msg.lower()
        t2 = store.get(t.task_id)
        assert t2.status == "durdu"


def test_engine_kisitli_otonom_with_approval_allows_write_local():
    """kisitli_otonom + genel onay açık: write_local adım yürütülür (simüle); doğrulama yok → dogrulanamadi."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Yaz", "özet ver", PROFILE_KISITLI_OTONOM)
        t.steps = [TaskStep("Dosyaya yaz", kind=STEP_TYPE_WRITE_LOCAL)]
        store.update(t)
        engine = TaskEngine(store, PROFILE_KISITLI_OTONOM, general_approval=True)
        ok, msg = engine.run_task(t.task_id)
        assert ok is True
        t2 = store.get(t.task_id)
        assert t2.status == "dogrulanamadi"


def test_task_persistence_after_reload():
    """Görev oluştur, kaydet; aynı dizinde yeni TaskStore ile açınca görev korunur (kapat-aç simülasyonu)."""
    with tempfile.TemporaryDirectory() as d:
        store1 = TaskStore(d)
        t = store1.create("Kalıcı görev", "not kontrol ve özet", PROFILE_GUVENLI_YURUT)
        tid = t.task_id
        store1._save()
        store2 = TaskStore(d)
        all_tasks = store2.list_all()
        assert len(all_tasks) >= 1
        found = store2.get(tid)
        assert found is not None
        assert found.title == "Kalıcı görev"
        assert found.status == "bekliyor"
        assert len(found.steps) >= 1


def test_flow_create_run_list_summary():
    """Akış: görev oluştur → yürüt → görevler listele → görev özeti al."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        engine = TaskEngine(store, PROFILE_GUVENLI_YURUT, True, base_dir=d)
        t = store.create("Akış testi", "not sistemini kontrol et ve özet ver", PROFILE_GUVENLI_YURUT)
        ok, msg = engine.run_task(t.task_id)
        assert ok is True
        tasks = store.list_all()
        assert len(tasks) >= 1
        t2 = store.get(t.task_id)
        assert t2 is not None
        assert t2.summary
        assert t2.status in ("tamamlandi", "kismi", "dogrulanamadi", "simulasyon")
        assert "Durum:" in t2.summary or "Geçen süre" in t2.summary


def test_second_task_creation():
    """İkinci görev düzgün oluşur; base_dir ile doğrulama yapılırsa her iki görev de tamamlandi olabilir."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        engine = TaskEngine(store, PROFILE_GUVENLI_YURUT, True, base_dir=d)
        t1 = store.create("Birinci", "not sistemini kontrol et ve kısa özet ver", PROFILE_RAPOR)
        t2 = store.create("İkinci", "not sistemini kontrol et ve kısa özet ver", PROFILE_GUVENLI_YURUT)
        assert t1.task_id == 1
        assert t2.task_id == 2
        engine_rapor = TaskEngine(store, PROFILE_RAPOR, False, base_dir=d)
        ok1, _ = engine_rapor.run_task(t1.task_id)
        ok2, _ = engine.run_task(t2.task_id)
        assert ok1 is True
        assert ok2 is True
        tasks = store.list_all()
        assert len(tasks) == 2
        g1 = store.get(1)
        g2 = store.get(2)
        assert g1 is not None and g1.title == "Birinci"
        assert g2 is not None and g2.title == "İkinci"
        assert g1.status != "tamamlandi", "rapor profili tamamlandi dönmez"
        assert g1.status in ("kismi", "simulasyon", "dogrulanamadi")
        assert g2.status in ("tamamlandi", "kismi"), "guvenli_yurut + doğrulama: tamamlandi veya kismi"
        assert g2.verified_count >= 1


def test_task_integrity_create_a_create_b_list_status_summary():
    """
    Kritik bütünlük: görev oluştur A, görev oluştur B; görevler; görev durumu 1/2; görev özeti 1/2.
    A/B açıklamalarında gerçek doğrulama yok → durum dogrulanamadi/simulasyon; içerik karışması olmasın.
    """
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        engine = TaskEngine(store, PROFILE_GUVENLI_YURUT, True)
        title_a, desc_a = "A", "Görev A açıklaması"
        title_b, desc_b = "B", "Görev B açıklaması"
        ta = store.create(title_a, desc_a, PROFILE_GUVENLI_YURUT)
        tb = store.create(title_b, desc_b, PROFILE_GUVENLI_YURUT)
        assert ta.task_id == 1
        assert tb.task_id == 2
        ok_a, _ = engine.run_task(ta.task_id)
        ok_b, _ = engine.run_task(tb.task_id)
        assert ok_a is True and ok_b is True
        g1 = store.get(1)
        g2 = store.get(2)
        assert g1 is not None and g1.title == title_a and g1.description == desc_a
        assert g2 is not None and g2.title == title_b and g2.description == desc_b
        assert g1.status != "tamamlandi"  # doğrulama yapılmadı
        assert g2.status != "tamamlandi"
        assert g1.summary and (desc_a[:20] in g1.summary or title_a in g1.summary or "Görev" in g1.summary)
        assert g2.summary and (desc_b[:20] in g2.summary or title_b in g2.summary or "Görev" in g2.summary)
        assert desc_b not in (g1.summary or "") and title_b not in (g1.summary or "")
        assert desc_a not in (g2.summary or "") and title_a not in (g2.summary or "")


def test_rapor_and_guvenli_yurut_with_base_dir_verified():
    """base_dir verildiğinde not kontrol gerçek okuma yapar; rapor asla tamamlandi vermez (kismi), guvenli_yurut=tamamlandi."""
    desc = "not sistemini kontrol et ve kısa özet ver"
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t_rapor = store.create("Rapor görev", desc, PROFILE_RAPOR)
        t_guvenli = store.create("Güvenli görev", desc, PROFILE_GUVENLI_YURUT)
        engine_rapor = TaskEngine(store, PROFILE_RAPOR, False, base_dir=d)
        engine_guvenli = TaskEngine(store, PROFILE_GUVENLI_YURUT, False, base_dir=d)
        ok_rapor, _ = engine_rapor.run_task(t_rapor.task_id)
        ok_guvenli, _ = engine_guvenli.run_task(t_guvenli.task_id)
        assert ok_rapor is True
        assert ok_guvenli is True
        r = store.get(t_rapor.task_id)
        g = store.get(t_guvenli.task_id)
        assert r.verified_count >= 1
        assert g.verified_count >= 1
        assert r.status != "tamamlandi", "rapor profili doğrulama olsa bile tamamlandi vermez"
        assert r.status == "kismi"
        assert g.status in ("tamamlandi", "kismi"), "guvenli_yurut + doğrulama: güçlü sonuç"
        assert g.verified_count >= 1


def test_guvenli_yurut_all_steps_verified_tamamlandi():
    """guvenli_yurut: tüm adımlar doğrulanırsa durum tamamlandi olur."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Kontrol", "not kontrol", PROFILE_GUVENLI_YURUT)
        # Tek adım: sadece not kontrol (READ) → doğrulama yapılır
        t.steps = [TaskStep("Not sistemini kontrol et", kind=STEP_TYPE_READ)]
        store.update(t)
        engine = TaskEngine(store, PROFILE_GUVENLI_YURUT, True, base_dir=d)
        ok, _ = engine.run_task(t.task_id)
        assert ok is True
        t2 = store.get(t.task_id)
        assert t2.verified_count == 1
        assert t2.status == "tamamlandi"


def test_rapor_unverifiable_task_not_tamamlandi():
    """rapor profili + doğrulanamayan görev (olmayan modülü analiz et) -> tamamlandi OLMAMALI."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Analiz", "olmayan modülü analiz et", PROFILE_RAPOR)
        engine = TaskEngine(store, PROFILE_RAPOR, False, base_dir=d)
        ok, _ = engine.run_task(t.task_id)
        assert ok is True
        t2 = store.get(t.task_id)
        assert t2.status != "tamamlandi"
        assert t2.status in ("simulasyon", "dogrulanamadi")
        assert t2.verified_count == 0


def test_guvenli_yurut_unverifiable_task_not_tamamlandi():
    """guvenli_yurut + doğrulanamayan görev (base_dir yok, sadece analiz adımları) -> tamamlandi OLMAMALI."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Analiz", "olmayan modülü analiz et", PROFILE_GUVENLI_YURUT)
        engine = TaskEngine(store, PROFILE_GUVENLI_YURUT, False)  # base_dir yok
        ok, _ = engine.run_task(t.task_id)
        assert ok is True
        t2 = store.get(t.task_id)
        assert t2.status != "tamamlandi"
        assert t2.status == "dogrulanamadi"
        assert t2.verified_count == 0


def test_gorev_ozeti_shows_verified_unverified():
    """görev özeti: doğrulanan, doğrulanamayan, simülasyon adım sayıları ve son durum görünmeli."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Kontrol", "not sistemini kontrol et ve özet ver", PROFILE_GUVENLI_YURUT)
        engine = TaskEngine(store, PROFILE_GUVENLI_YURUT, True, base_dir=d)
        engine.run_task(t.task_id)
        t2 = store.get(t.task_id)
        assert "Doğrulanan adım:" in t2.summary
        assert "Doğrulanamayan adım:" in t2.summary
        assert "Simülasyon adım:" in t2.summary
        assert "Durum:" in t2.summary
        assert t2.verified_count >= 1
        assert t2.unverified_count >= 0
        assert getattr(t2, "simulation_count", 0) >= 0
        assert t2.status in ("tamamlandi", "kismi", "dogrulanamadi", "simulasyon")


def test_step_result_kind_after_run():
    """Her adım bittiğinde result_kind set edilir: tamamlandi, simulasyon, dogrulanamadi veya hata."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Kontrol", "not sistemini kontrol et ve özet ver", PROFILE_GUVENLI_YURUT)
        engine = TaskEngine(store, PROFILE_GUVENLI_YURUT, True, base_dir=d)
        engine.run_task(t.task_id)
        t2 = store.get(t.task_id)
        for s in t2.steps:
            if s.status == "tamamlandi":
                assert s.result_kind in ("tamamlandi", "simulasyon"), f"Adım {s.title!r} result_kind: {s.result_kind!r}"
            elif s.status == "hata":
                assert s.result_kind == "hata"
        assert t2.simulation_count >= 0
        assert t2.verified_count + t2.unverified_count == sum(
            1 for s in t2.steps if s.status == "tamamlandi"
        )
