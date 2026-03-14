"""Note-related CLI handlers for Lumos core.

Extracted from main.py and cli_readonly for stabilization. Handles note listing,
viewing, search, help text, and note-scoped command routing (including mutations
to in-memory saved_notes). No lock/presence/task or workspace_contract changes.
"""
from __future__ import annotations

from typing import Any

from cli.cli_parse import (
    HATIRLA_NOTE_MAX_LEN,
    HELP_ARAMA_TEXT,
    HELP_NOT_ISLEMLERI_TEXT,
    HELP_NOTLAR_TEXT,
    NOT_ADLANDIR_MAX_TAG_LEN,
    NOT_OZETLE_SHORT_THRESHOLD,
    _fold_for_search,
    _shorten_previous_response,
)
from cli.cli_readonly import ReadOnlyContext


def handle_notes(
    route: str,
    args: list[str],
    ctx: ReadOnlyContext,
    cli_mode: list[str],
    last_note_undo: list[Any | None],
) -> bool:
    """Handle note-scoped routes: listing, viewing, search, help, and note mutations.
    Returns True if the route was handled, False otherwise.
    """
    # ---- Note help ----
    if route == "help_notlar":
        ctx.last_response_reason[0] = "not komutlarını istedin"
        ctx.last_action[0] = "En son not yardımını gösterdim."
        ctx.record_today_action(ctx.last_action[0])
        ctx.last_response_text[0] = HELP_NOTLAR_TEXT
        print(HELP_NOTLAR_TEXT)
        return True
    if route == "help_not_islemleri":
        ctx.last_response_reason[0] = "not işlem komutlarını istedin"
        ctx.last_action[0] = "En son not işlemleri yardımını gösterdim."
        ctx.record_today_action(ctx.last_action[0])
        ctx.last_response_text[0] = HELP_NOT_ISLEMLERI_TEXT
        print(HELP_NOT_ISLEMLERI_TEXT)
        return True
    if route == "help_arama":
        ctx.last_response_reason[0] = "arama komutlarını istedin"
        ctx.last_action[0] = "En son arama yardımını gösterdim."
        ctx.record_today_action(ctx.last_action[0])
        ctx.last_response_text[0] = HELP_ARAMA_TEXT
        print(HELP_ARAMA_TEXT)
        return True

    # ---- Note listing / viewing (read-only) ----
    if route == "son_not_ne":
        if ctx.saved_notes[0]:
            print("Son not: " + ctx.saved_notes[0][-1])
        else:
            print("Henüz kayıtlı bir not yok.")
        return True
    if route == "notu_kopyala":
        if ctx.saved_notes[0]:
            ctx.record_note_op("notu kopyala")
            print(ctx.saved_notes[0][-1])
        else:
            print("Kopyalanacak kayıtlı not yok.")
        return True
    if route == "notu_disa_aktar":
        if ctx.saved_notes[0]:
            ctx.record_note_op("notu dışa aktar")
            print(ctx.saved_notes[0][-1])
        else:
            print("Dışa aktarılacak kayıtlı not yok.")
        return True
    if route == "notu_paylas":
        if ctx.saved_notes[0]:
            ctx.record_note_op("notu paylaş")
            print(ctx.saved_notes[0][-1])
        else:
            print("Paylaşılacak kayıtlı not yok.")
        return True
    if route == "not_ozetle":
        if not ctx.saved_notes[0]:
            print("Özetlenecek kayıtlı not yok.")
        else:
            ctx.record_note_op("not özetle")
            last_note = ctx.saved_notes[0][-1].strip()
            if len(last_note) <= NOT_OZETLE_SHORT_THRESHOLD:
                print("Son not zaten yeterince kısa.")
            else:
                short = _shorten_previous_response(last_note).strip()
                if not short:
                    short = (last_note[:120].rsplit(maxsplit=1)[0].rstrip(".,") + ".") if len(last_note) > 120 else last_note
                print("Kısa özet: " + short)
        return True
    if route == "notlari_goster":
        if not ctx.saved_notes[0]:
            print("Henüz kayıtlı not yok.")
        else:
            recent = ctx.saved_notes[0][-5:]
            print("Kayıtlı notlar:")
            for n in recent:
                print("- " + n)
        return True
    if route == "etiketli_notlari_goster":
        tagged = [n for n in ctx.saved_notes[0] if n.startswith("[") and "] " in n]
        if not tagged:
            print("Henüz etiketli not yok.")
        else:
            recent_tagged = tagged[-5:]
            print("Etiketli notlar:")
            for n in recent_tagged:
                print("- " + n)
        return True
    if route == "etikete_gore_notlari_goster":
        tag_raw = (args[0] if args else "").strip()
        if not tag_raw:
            print("Göstermek için bir etiket yazman gerekiyor.")
            return True
        tagged = [n for n in ctx.saved_notes[0] if n.startswith("[") and "] " in n]
        folded = _fold_for_search(tag_raw)
        matches = [n for n in tagged if _fold_for_search(n[1 : n.index("] ")].strip()) == folded]
        if not matches:
            print("Bu etikete sahip not bulamadım.")
        else:
            recent = matches[-5:]
            print("Eşleşen notlar:")
            for n in recent:
                print("- " + n)
        return True
    if route == "etiketleri_goster":
        seen: set[str] = set()
        tags_ordered: list[str] = []
        for n in reversed(ctx.saved_notes[0]):
            if n.startswith("[") and "] " in n:
                tag = n[1 : n.index("] ")].strip()
                if tag and tag not in seen:
                    seen.add(tag)
                    tags_ordered.append(tag)
        if not tags_ordered:
            print("Henüz kayıtlı etiket yok.")
        else:
            print("Kayıtlı etiketler:")
            for t in tags_ordered:
                print("- " + t)
        return True
    if route == "etiket_ara":
        word = (args[0] if args else "").strip()
        if not word:
            print("Aramak için bir etiket yazman gerekiyor.")
            return True
        seen_tag: set[str] = set()
        tags_ordered_etiket_ara: list[str] = []
        for n in reversed(ctx.saved_notes[0]):
            if n.startswith("[") and "] " in n:
                tag = n[1 : n.index("] ")].strip()
                if tag and tag not in seen_tag:
                    seen_tag.add(tag)
                    tags_ordered_etiket_ara.append(tag)
        folded = _fold_for_search(word)
        matched = [t for t in tags_ordered_etiket_ara if folded in _fold_for_search(t)]
        if not matched:
            print("Bu aramayla eşleşen etiket bulamadım.")
        else:
            print("Eşleşen etiketler:")
            for t in matched:
                print("- " + t)
        return True
    if route == "not_gecmisi":
        if not ctx.note_ops_history[0]:
            print("Henüz kayıtlı not işlemi yok.")
        else:
            print("Son not işlemleri:")
            for op in reversed(ctx.note_ops_history[0]):
                print("- " + op)
        return True
    if route == "kac_not_var":
        n = len(ctx.saved_notes[0])
        if n == 0:
            print("Kayıtlı not yok.")
        else:
            print(f"{n} kayıtlı not var.")
        return True
    if route == "not_ara":
        word = (args[0] if args else "").strip()
        if not word:
            print("Aramak için bir kelime yazman gerekiyor.")
            return True
        ctx.record_note_op("not ara")
        folded = _fold_for_search(word)
        matches = [n for n in ctx.saved_notes[0] if folded in _fold_for_search(n)]
        if not matches:
            print("Bu aramayla eşleşen not bulamadım.")
        else:
            recent = matches[-5:]
            print("Eşleşen notlar:")
            for n in recent:
                print("- " + n)
        return True
    if route == "etiketli_not_ara":
        word = (args[0] if args else "").strip()
        if not word:
            print("Aramak için bir kelime yazman gerekiyor.")
            return True
        tagged = [n for n in ctx.saved_notes[0] if n.startswith("[") and "] " in n]
        folded = _fold_for_search(word)
        matches = [n for n in tagged if folded in _fold_for_search(n)]
        if not matches:
            print("Bu aramayla eşleşen etiketli not bulamadım.")
        else:
            print("Eşleşen etiketli notlar:")
            for n in matches:
                print("- " + n)
        return True

    # ---- Note mutations (in-memory saved_notes only) ----
    CLI_NOT_BEKLEME = "not_bekleme_modu"
    CLI_NOT_DUZENLEME = "not_duzenleme_modu"

    if route == "hatirla":
        note_rest = (args[0].strip() if args else "")
        if note_rest:
            if len(note_rest) > HATIRLA_NOTE_MAX_LEN:
                note_rest = (note_rest[:HATIRLA_NOTE_MAX_LEN].rsplit(maxsplit=1)[0].rstrip(".,") or note_rest[:HATIRLA_NOTE_MAX_LEN])
            ctx.saved_notes[0].append(note_rest)
            ctx.record_note_op("bunu hatırla")
            ctx.last_response_reason[0] = "bunu hatırla dedin"
            ctx.last_action[0] = "En son hatırla işlemini yaptım."
            ctx.last_response_text[0] = "Bunu not ettim."
            ctx.record_today_action(ctx.last_action[0])
            print("Bunu not ettim.")
        else:
            cli_mode[0] = CLI_NOT_BEKLEME
            ctx.last_response_reason[0] = "bunu hatırla dedin"
            ctx.last_action[0] = "En son hatırla istedin; not metnini bekliyorum."
            print("Ne hatırlayayım?")
        return True
    if route == "notlari_temizle":
        if not ctx.saved_notes[0]:
            print("Temizlenecek kayıtlı not yok.")
        else:
            last_note_undo[0] = ("notlari_temizle", ctx.saved_notes[0][:])
            ctx.saved_notes[0].clear()
            ctx.record_note_op("notları temizle")
            print("Kayıtlı notları temizledim.")
        return True
    if route == "notu_sil":
        if not ctx.saved_notes[0]:
            print("Silinecek kayıtlı not yok.")
        else:
            last_note_undo[0] = ("notu_sil", ctx.saved_notes[0][-1])
            ctx.saved_notes[0].pop()
            ctx.record_note_op("notu sil")
            print("Son notu sildim.")
        return True
    if route == "notu_duzenle":
        if not ctx.saved_notes[0]:
            print("Düzenlenecek kayıtlı not yok.")
        else:
            inline_text = (args[0] if args else "").strip()
            if inline_text:
                if len(inline_text) > HATIRLA_NOTE_MAX_LEN:
                    inline_text = (inline_text[:HATIRLA_NOTE_MAX_LEN].rsplit(maxsplit=1)[0].rstrip(".,") or inline_text[:HATIRLA_NOTE_MAX_LEN])
                old_content = ctx.saved_notes[0][-1]
                ctx.saved_notes[0][-1] = inline_text
                last_note_undo[0] = ("notu_duzenle", old_content)
                ctx.record_note_op("notu düzenle")
                ctx.last_action[0] = "En son notu düzenledim."
                print("Son notu güncelledim.")
            else:
                cli_mode[0] = CLI_NOT_DUZENLEME
                print("Son notu düzenlemek için yeni kısa metni yaz.")
        return True
    if route == "notu_adlandir":
        tag_raw = (args[0] if args else "").strip()
        if not tag_raw:
            print("Etiket için kısa bir ad yazman gerekiyor.")
            return True
        if not ctx.saved_notes[0]:
            print("Etiketlenecek kayıtlı not yok.")
            return True
        tag = tag_raw
        if len(tag) > NOT_ADLANDIR_MAX_TAG_LEN:
            tag = tag[:NOT_ADLANDIR_MAX_TAG_LEN].strip()
        old_content = ctx.saved_notes[0][-1]
        ctx.saved_notes[0][-1] = "[" + tag + "] " + old_content
        last_note_undo[0] = ("notu_duzenle", old_content)
        ctx.record_note_op("notu adlandır")
        print("Son notu etiketledim.")
        return True
    if route == "etiket_kaldir":
        tag_raw = (args[0] if args else "").strip()
        if not tag_raw:
            print("Kaldırmak için bir etiket yazman gerekiyor.")
            return True
        if not ctx.saved_notes[0]:
            print("Etiketi kaldıracak kayıtlı not yok.")
            return True
        last = ctx.saved_notes[0][-1]
        if not last.startswith("[") or "] " not in last:
            print("Son notta bu etiket yok.")
            return True
        idx = last.index("] ")
        tag_in_note = last[1:idx].strip()
        if _fold_for_search(tag_in_note) != _fold_for_search(tag_raw):
            print("Son notta bu etiket yok.")
            return True
        rest = last[idx + 2 :].strip()
        ctx.saved_notes[0][-1] = rest
        last_note_undo[0] = ("notu_duzenle", last)
        ctx.record_note_op("etiket kaldır")
        print("Etiketi kaldırdım.")
        return True
    if route == "etiket_degistir":
        eski_raw = (args[0] if len(args) > 0 else "").strip()
        yeni_raw = (args[1] if len(args) > 1 else "").strip()
        if not eski_raw or not yeni_raw:
            print("Eski ve yeni etiket yazman gerekiyor.")
            return True
        if not ctx.saved_notes[0]:
            print("Etiket değiştirilecek kayıtlı not yok.")
            return True
        last = ctx.saved_notes[0][-1]
        if not last.startswith("[") or "] " not in last:
            print("Son notta bu etiket yok.")
            return True
        idx = last.index("] ")
        tag_in_note = last[1:idx].strip()
        if _fold_for_search(tag_in_note) != _fold_for_search(eski_raw):
            print("Son notta bu etiket yok.")
            return True
        yeni = yeni_raw
        if len(yeni) > NOT_ADLANDIR_MAX_TAG_LEN:
            yeni = yeni[:NOT_ADLANDIR_MAX_TAG_LEN].strip()
        rest = last[idx + 2 :].strip()
        ctx.saved_notes[0][-1] = "[" + yeni + "] " + rest
        last_note_undo[0] = ("notu_duzenle", last)
        ctx.record_note_op("etiket değiştir")
        print("Etiketi güncelledim.")
        return True
    if route == "not_birlestir":
        if len(ctx.saved_notes[0]) < 2:
            print("Birleştirmek için en az 2 kayıtlı not gerekiyor.")
        else:
            last_two = [ctx.saved_notes[0][-2].strip(), ctx.saved_notes[0][-1].strip()]
            merged = (last_two[0] + " " + last_two[1]).strip()
            if len(merged) > 240:
                merged = (merged[:240].rsplit(maxsplit=1)[0].rstrip(".,") + ".").strip() or merged[:240]
            ctx.saved_notes[0].append(merged)
            last_note_undo[0] = ("not_birlestir", None)
            ctx.record_note_op("not birleştir")
            print("Son iki notu birleştirdim.")
        return True
    if route == "notu_geri_al":
        u = last_note_undo[0]
        if not u:
            print("Geri alınacak uygun bir not işlemi yok.")
        else:
            op, data = u
            if op == "notu_sil":
                ctx.saved_notes[0].append(data)
            elif op == "notlari_temizle":
                ctx.saved_notes[0][:] = data
            elif op == "notu_duzenle":
                ctx.saved_notes[0][-1] = data
            elif op == "not_birlestir":
                ctx.saved_notes[0].pop()
            last_note_undo[0] = None
            ctx.record_note_op("notu geri al")
            print("Son not işlemini geri aldım.")
        return True

    return False
