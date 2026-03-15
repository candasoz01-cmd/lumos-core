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
    may_execute_step_at_runtime,
    STEP_TYPE_ANALYZE,
    STEP_TYPE_READ,
    STEP_TYPE_PLAN,
    STEP_TYPE_SAFE_LOCAL,
    STEP_TYPE_WRITE_LOCAL,
    STEP_TYPE_EXTERNAL,
    STEP_TYPE_CRITICAL,
    STEP_PERMISSION_MATRIX,
    DECISION_LAYER_ANALYZE,
    DECISION_LAYER_SUGGEST,
    DECISION_LAYER_APPLY,
    DECISION_LAYER_NEVER,
    get_decision_layer,
    requires_explicit_approval,
)
from task_engine.engine import (
    TaskStep,
    compute_task_stats,
    find_recent_similar_task,
)


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


def test_explicit_approval_required_for_application_steps():
    """Açık onay guard: uygulama adımları (safe_local, write_local) raporda asla; kisitli_otonom'da yalnızca general_approval True iken."""
    for app_step in (STEP_TYPE_SAFE_LOCAL, STEP_TYPE_WRITE_LOCAL):
        assert is_allowed_for_profile(PROFILE_RAPOR, app_step, False) is False
        assert is_allowed_for_profile(PROFILE_RAPOR, app_step, True) is False
        assert is_allowed_for_profile(PROFILE_KISITLI_OTONOM, app_step, False) is False
        assert is_allowed_for_profile(PROFILE_KISITLI_OTONOM, app_step, True) is True


def test_step_permission_matrix_matches_contract():
    """Yetki matrisi: profil × adım türü × genel onay dokümantasyonla birebir hizalı olmalı."""
    perm_analyze = STEP_PERMISSION_MATRIX[STEP_TYPE_ANALYZE]
    assert perm_analyze.decision_layer == DECISION_LAYER_ANALYZE
    assert perm_analyze.allowed_without_approval == perm_analyze.allowed_with_approval == frozenset(
        {PROFILE_RAPOR, PROFILE_GUVENLI_YURUT, PROFILE_KISITLI_OTONOM}
    )

    perm_read = STEP_PERMISSION_MATRIX[STEP_TYPE_READ]
    assert perm_read.decision_layer == DECISION_LAYER_ANALYZE

    perm_plan = STEP_PERMISSION_MATRIX[STEP_TYPE_PLAN]
    assert perm_plan.decision_layer == DECISION_LAYER_SUGGEST

    perm_safe = STEP_PERMISSION_MATRIX[STEP_TYPE_SAFE_LOCAL]
    assert perm_safe.decision_layer == DECISION_LAYER_APPLY
    assert perm_safe.allowed_without_approval == frozenset({PROFILE_GUVENLI_YURUT})
    assert perm_safe.allowed_with_approval == frozenset({PROFILE_GUVENLI_YURUT, PROFILE_KISITLI_OTONOM})

    perm_write = STEP_PERMISSION_MATRIX[STEP_TYPE_WRITE_LOCAL]
    assert perm_write.decision_layer == DECISION_LAYER_APPLY
    assert perm_write.allowed_without_approval == frozenset()
    assert perm_write.allowed_with_approval == frozenset({PROFILE_KISITLI_OTONOM})

    perm_external = STEP_PERMISSION_MATRIX[STEP_TYPE_EXTERNAL]
    perm_critical = STEP_PERMISSION_MATRIX[STEP_TYPE_CRITICAL]
    for perm in (perm_external, perm_critical):
        assert perm.decision_layer == DECISION_LAYER_NEVER
        assert perm.allowed_without_approval == frozenset()
        assert perm.allowed_with_approval == frozenset()

    # Karar katmanı yardımcı fonksiyonu ile hizalı olmalı
    assert get_decision_layer(STEP_TYPE_ANALYZE) == DECISION_LAYER_ANALYZE
    assert get_decision_layer(STEP_TYPE_PLAN) == DECISION_LAYER_SUGGEST
    assert get_decision_layer(STEP_TYPE_SAFE_LOCAL) == DECISION_LAYER_APPLY
    assert get_decision_layer(STEP_TYPE_WRITE_LOCAL) == DECISION_LAYER_APPLY
    assert get_decision_layer(STEP_TYPE_EXTERNAL) == DECISION_LAYER_NEVER
    assert get_decision_layer("bilinmeyen_tur") == DECISION_LAYER_NEVER


def test_requires_explicit_approval_for_application_layers():
    """Genel onay gerektiren uygulama adımları merkezi yardımcı ile net görülebilmeli."""
    # kisitli_otonom: safe_local ve write_local yalnızca genel onay açıkken izinli (yapısal olarak)
    assert requires_explicit_approval(PROFILE_KISITLI_OTONOM, STEP_TYPE_SAFE_LOCAL, False) is True
    assert requires_explicit_approval(PROFILE_KISITLI_OTONOM, STEP_TYPE_SAFE_LOCAL, True) is True
    assert requires_explicit_approval(PROFILE_KISITLI_OTONOM, STEP_TYPE_WRITE_LOCAL, False) is True
    assert requires_explicit_approval(PROFILE_KISITLI_OTONOM, STEP_TYPE_WRITE_LOCAL, True) is True

    # guvenli_yurut: safe_local genel onaydan bağımsız serbest, write_local asla izinli değil
    assert requires_explicit_approval(PROFILE_GUVENLI_YURUT, STEP_TYPE_SAFE_LOCAL, False) is False
    assert requires_explicit_approval(PROFILE_GUVENLI_YURUT, STEP_TYPE_SAFE_LOCAL, True) is False
    assert requires_explicit_approval(PROFILE_GUVENLI_YURUT, STEP_TYPE_WRITE_LOCAL, False) is False
    assert requires_explicit_approval(PROFILE_GUVENLI_YURUT, STEP_TYPE_WRITE_LOCAL, True) is False

    # rapor: hiçbir uygulama adımı izinli değil, dolayısıyla açık onay gerektiren uygulama adımı da yok
    assert requires_explicit_approval(PROFILE_RAPOR, STEP_TYPE_SAFE_LOCAL, False) is False
    assert requires_explicit_approval(PROFILE_RAPOR, STEP_TYPE_SAFE_LOCAL, True) is False
    assert requires_explicit_approval(PROFILE_RAPOR, STEP_TYPE_WRITE_LOCAL, False) is False
    assert requires_explicit_approval(PROFILE_RAPOR, STEP_TYPE_WRITE_LOCAL, True) is False


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


def test_engine_kisitli_otonom_no_approval_blocks_safe_local():
    """kisitli_otonom + genel onay kapalı: safe_local adım da çalışmaz (uygulama katmanı, açık onay gerektirir)."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Yerel güvenli iş", "özet ver", PROFILE_KISITLI_OTONOM)
        t.steps = [TaskStep("Yerel güvenli iş", kind=STEP_TYPE_SAFE_LOCAL)]
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


# --- Runtime step enforcement paketi: adım türü + profil + onay runtime'da zorlanır ---


def test_runtime_step_enforcement_external_and_critical_always_rejected():
    """Runtime enforcement: external/critical adımlar hiçbir profil ve onayla yürütülmez; run_task ilk adımda durur."""
    for step_type in (STEP_TYPE_EXTERNAL, STEP_TYPE_CRITICAL):
        for profile in (PROFILE_RAPOR, PROFILE_GUVENLI_YURUT, PROFILE_KISITLI_OTONOM):
            with tempfile.TemporaryDirectory() as d:
                store = TaskStore(d)
                t = store.create("X", "desc", profile)
                t.steps = [TaskStep("Dış/kritik iş", kind=step_type)]
                store.update(t)
                engine = TaskEngine(store, profile, general_approval=True)
                ok, msg = engine.run_task(t.task_id)
                assert ok is False, f"{profile} + {step_type} should be rejected at runtime"
                t2 = store.get(t.task_id)
                assert t2.status == "durdu"
                step = next(s for s in t2.steps if s.status == "durdu")
                # unsupported_action: "Desteklenmeyen adım türü (bu adım güvenlik politikası gereği çalıştırılamaz)."
                assert (
                    "güvenlik politikası" in step.error.lower()
                    or "çalıştırılamaz" in step.error.lower()
                    or "yetki" in step.error.lower()
                    or "onay" in step.error.lower()
                    or "kapsam" in step.error.lower()
                )


def test_runtime_step_enforcement_analyze_allowed_rapor_without_approval():
    """Runtime enforcement: analiz adımı rapor profilde genel onay olmadan yürütülebilir; uygulama adımı değil."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Analiz", "sadece analiz", PROFILE_RAPOR)
        t.steps = [TaskStep("Analiz et", kind=STEP_TYPE_ANALYZE)]
        store.update(t)
        engine = TaskEngine(store, PROFILE_RAPOR, general_approval=False)
        ok, msg = engine.run_task(t.task_id)
        assert ok is True, "analyze step must run under rapor without approval"
        assert may_execute_step_at_runtime(PROFILE_RAPOR, STEP_TYPE_ANALYZE, False) is True
        assert may_execute_step_at_runtime(PROFILE_RAPOR, STEP_TYPE_SAFE_LOCAL, False) is False


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


def test_task_store_persistence_with_archive_flags():
    """Arşiv bilgisi (archived, archived_at) kalıcı; yeniden yüklendiğinde korunur."""
    with tempfile.TemporaryDirectory() as d:
        store1 = TaskStore(d)
        t = store1.create("Kalıcı görev", "not kontrol ve özet", PROFILE_GUVENLI_YURUT)
        tid = t.task_id
        # Görevi tamamlanmış kabul edip arşivle
        t.status = "tamamlandi"
        store1.update(t)
        count = store1.archive_completed()
        assert count == 1
        store2 = TaskStore(d)
        t2 = store2.get(tid)
        assert t2 is not None
        assert t2.archived is True
        assert isinstance(t2.archived_at, str)
        assert t2.status == "tamamlandi"


def test_archive_completed_and_simulations():
    """Tamamlanan ve simulasyon görevleri arşivlenir; diğer durumlar dokunulmaz."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        g1 = store.create("T1", "a", PROFILE_GUVENLI_YURUT)
        g2 = store.create("T2", "b", PROFILE_GUVENLI_YURUT)
        g3 = store.create("T3", "c", PROFILE_GUVENLI_YURUT)
        g1.status = "tamamlandi"
        g2.status = "simulasyon"
        g3.status = "kismi"
        store.update(g1)
        store.update(g2)
        store.update(g3)

        c1 = store.archive_completed()
        assert c1 == 1
        c2 = store.archive_simulations()
        assert c2 == 1

        ng1 = store.get(g1.task_id)
        ng2 = store.get(g2.task_id)
        ng3 = store.get(g3.task_id)
        assert ng1.archived is True and ng1.status == "tamamlandi"
        assert ng2.archived is True and ng2.status == "simulasyon"
        assert ng3.archived is False and ng3.status == "kismi"


def test_archive_vs_delete_single_task():
    """Arşivle/sil ayrımı: arşivlenen kalır; silme yalnızca açık kullanıcı iradesiyle (user_initiated=True)."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        g1 = store.create("A", "desc", PROFILE_GUVENLI_YURUT)
        g2 = store.create("B", "desc", PROFILE_GUVENLI_YURUT)
        store.archive(g1.task_id)
        assert store.get(g1.task_id).archived is True
        # Kalıcı silme sözleşmesi: yalnızca açık kullanıcı iradesiyle delete başarılı olur
        ok2 = store.delete(g2.task_id, user_initiated=True)
        assert ok2 is True, "delete(task_id, user_initiated=True) sözleşmeye uygun olarak True dönmeli"
        assert store.get(g2.task_id) is None
        # Arşivli görev de aynı sözleşmeyle (açık irade) kalıcı silinebilir
        ok1 = store.delete(g1.task_id, user_initiated=True)
        assert ok1 is True, "arşivli görev delete(..., user_initiated=True) ile silinebilmeli"
        assert store.get(g1.task_id) is None


def test_delete_requires_user_initiated():
    """Kalıcı silme guard: user_initiated=False iken delete hiçbir şey silmez."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        g = store.create("X", "desc", PROFILE_GUVENLI_YURUT)
        assert store.get(g.task_id) is not None
        assert store.delete(g.task_id, user_initiated=False) is False
        assert store.get(g.task_id) is not None
        assert store.delete(g.task_id, user_initiated=True) is True
        assert store.get(g.task_id) is None


def test_task_stats_summary_counts():
    """compute_task_stats: toplam, aktif, tamamlandı, kısmi, doğrulanamadı, simulasyon, arşiv sayaçları."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        g1 = store.create("Aktif", "a", PROFILE_GUVENLI_YURUT)
        g2 = store.create("Tamam", "b", PROFILE_GUVENLI_YURUT)
        g3 = store.create("Kısmi", "c", PROFILE_GUVENLI_YURUT)
        g4 = store.create("Doğrulanamadı", "d", PROFILE_GUVENLI_YURUT)
        g5 = store.create("Sim", "e", PROFILE_GUVENLI_YURUT)

        g1.status = "bekliyor"
        g2.status = "tamamlandi"
        g3.status = "kismi"
        g4.status = "dogrulanamadi"
        g5.status = "simulasyon"
        store.update(g1)
        store.update(g2)
        store.update(g3)
        store.update(g4)
        store.update(g5)

        # Bir tanesini arşivle
        store.archive(g2.task_id)
        stats = compute_task_stats(store.list_all())
        assert stats["toplam"] == 5
        assert stats["aktif"] == 1  # sadece bekliyor
        assert stats["tamamlandi"] == 1
        assert stats["kismi"] == 1
        assert stats["dogrulanamadi"] == 1
        assert stats["simulasyon"] == 1
        assert stats["arsiv"] == 1


def test_find_recent_similar_task_window_and_profile():
    """Aynı açıklama + profil + pencere içinde → benzer görev; farklı profil veya eski kayıtlar hariç."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        g1 = store.create("G1", "Açıklama", PROFILE_GUVENLI_YURUT)
        store.create("G2", "Açıklama", PROFILE_RAPOR)
        tasks = store.list_all()

        # Zaman damgalarını sahteleyerek pencere testini deterministik yap
        import time as _t

        now = _t.time()
        old_ts = now - 3600
        for t in tasks:
            if t.task_id == g1.task_id:
                t.created_at = _t.strftime("%Y-%m-%dT%H:%M:%S", _t.localtime(now))
            else:
                t.created_at = _t.strftime("%Y-%m-%dT%H:%M:%S", _t.localtime(old_ts))
            store.update(t)

        # Aynı profil + açıklama + pencere içinde → g1
        sim = find_recent_similar_task(
            store.list_all(), "Açıklama", PROFILE_GUVENLI_YURUT, now_ts=now, window_seconds=600
        )
        assert sim is not None and sim.task_id == g1.task_id

        # Farklı profil → None
        sim2 = find_recent_similar_task(
            store.list_all(), "Açıklama", PROFILE_RAPOR, now_ts=now, window_seconds=600
        )
        assert sim2 is None

        # Pencere dışında → None
        sim3 = find_recent_similar_task(
            store.list_all(), "Açıklama", PROFILE_GUVENLI_YURUT, now_ts=now, window_seconds=10
        )
        assert sim3 is None
