"""
Curses-based terminal panel (TUI) for Lumos Core.
Black background, white text; selected row in reverse video.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Any

try:
    import curses
except ImportError:
    curses = None  # type: ignore


LABEL_WIDTH = 22  # width reserved for prefix + label; description starts after

LOG_VIEWER_TITLE = "Lumos Log Viewer"
LOG_VIEWER_HINT = "↑↓ kaydır | PgUp/PgDn hızlı kaydır | q geri"
LOG_VIEWER_LINES = 200


def _log_line_attr(line: str) -> int:
    if "presence_enabled" in line:
        return curses.A_DIM
    if "device_locked" in line:
        return curses.A_BOLD
    return curses.A_NORMAL


def _run_log_viewer(stdscr, log_path: Path) -> None:
    """Log viewer: last 200 lines, scroll, presence_enabled=dim, device_locked=bold."""
    lines: list[str] = []
    if log_path.exists():
        try:
            raw = log_path.read_text(encoding="utf-8", errors="replace")
            lines = raw.strip().splitlines()[-LOG_VIEWER_LINES:]
        except Exception:
            lines = []
    scroll = 0
    h, w = stdscr.getmaxyx()
    content_h = max(0, h - 3)

    while True:
        stdscr.clear()
        title = LOG_VIEWER_TITLE[: w - 1]
        try:
            stdscr.addstr(0, max(0, (w - len(title)) // 2), title, curses.A_BOLD)
        except curses.error:
            pass
        scroll = max(0, min(scroll, max(0, len(lines) - content_h)))
        for i in range(content_h):
            li = scroll + i
            if li < len(lines):
                line = lines[li][: w - 1].replace("\t", " ")
                attr = _log_line_attr(lines[li])
                try:
                    stdscr.addstr(2 + i, 0, line, attr)
                except curses.error:
                    pass
        if h > 1:
            try:
                stdscr.addstr(h - 1, 0, LOG_VIEWER_HINT[: w - 1], curses.A_DIM)
            except curses.error:
                pass
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord("q"), ord("Q"), 27):
            break
        if key in (curses.KEY_UP, ord("k")):
            scroll = max(0, scroll - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            scroll = min(max(0, len(lines) - content_h), scroll + 1)
        elif key == curses.KEY_PPAGE:
            scroll = max(0, scroll - content_h)
        elif key == curses.KEY_NPAGE:
            scroll = min(max(0, len(lines) - content_h), scroll + content_h)


def run_tui(
    title: str,
    items: list[tuple[str, Callable[[], None] | None]],
    hint: str = "↑↓ seç, Enter onay, q çıkış",
    title_line2: str = "",
    status_getter: Callable[[], str] | None = None,
    descriptions: list[str] | None = None,
    log_path: Path | None = None,
    log_item_index: int | None = None,
    lock_status_getter: Callable[[], str] | None = None,
    presence_status_getter: Callable[[], str] | None = None,
    mode_str: str = "offline",
    snapshot_getter: Callable[[], dict[str, Any]] | None = None,
) -> None:
    """
    Run the TUI menu. If snapshot_getter is set, status line under title comes from CoreState.snapshot().
    """
    if curses is None:
        raise RuntimeError("curses not available")

    def main(stdscr) -> None:
        curses.curs_set(0)
        stdscr.keypad(True)
        try:
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_RED, -1)    # LOCKED
            curses.init_pair(2, curses.COLOR_GREEN, -1)  # UNLOCKED
            curses.init_pair(3, curses.COLOR_YELLOW, -1) # Presence ON
        except Exception:
            pass

        idx = 0
        n = len(items)

        def draw() -> None:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            row_pos = 0
            try:
                stdscr.addstr(row_pos, 0, title[: w - 1], curses.A_BOLD)
                row_pos += 1
            except curses.error:
                row_pos += 1
            if title_line2 and row_pos < h:
                try:
                    stdscr.addstr(row_pos, 0, title_line2[: w - 1], curses.A_DIM)
                    row_pos += 1
                except curses.error:
                    row_pos += 1
            # Status line: ● LOCKED/UNLOCKED ● Presence OFF | ON (running) | ON (stopped) ● offline
            if row_pos < h:
                try:
                    if snapshot_getter:
                        snap = snapshot_getter()
                        lock = (snap.get("lock_status") or "-").strip().upper()
                        enabled = bool(snap.get("presence_enabled", False))
                        running = bool(snap.get("presence_running", False))
                        presence = "OFF"
                        if enabled:
                            presence = "ON (running)" if running else "ON (stopped)"
                        mode = (snap.get("mode") or "offline").strip().lower()
                    else:
                        lock = (lock_status_getter() or "-").strip().upper() if lock_status_getter else "-"
                        presence = (presence_status_getter() or "-").strip() if presence_status_getter else "-"
                        mode = (mode_str or "offline").strip().lower()
                    c1 = curses.color_pair(1) if lock == "LOCKED" else curses.color_pair(2)
                    if "running" in presence.lower():
                        c2 = curses.color_pair(3)
                    elif "stopped" in presence.lower():
                        c2 = curses.color_pair(1) | curses.A_DIM
                    else:
                        c2 = curses.A_DIM
                    parts = [f"● {lock}", f"● Presence {presence}", f"● {mode}"]
                    col = 0
                    for i, seg in enumerate(parts):
                        if col >= w - 1:
                            break
                        attr = c1 if i == 0 else (c2 if i == 1 else curses.A_DIM)
                        stdscr.addstr(row_pos, col, seg[: w - col - 1], attr)
                        col += len(seg) + 2
                    row_pos += 1
                except (curses.error, Exception):
                    row_pos += 1
            row_pos += 1  # blank before menu
            # Menu (prefix + label, then dim description at LABEL_WIDTH)
            menu_start = row_pos
            for i, (label, _) in enumerate(items):
                r = menu_start + i
                if r >= h - 2:
                    break
                prefix = "  "
                attr = curses.A_NORMAL
                if i == idx:
                    prefix = "› "
                    attr = curses.A_REVERSE | curses.A_BOLD
                label_text = (prefix + label)[: LABEL_WIDTH].ljust(LABEL_WIDTH)
                try:
                    stdscr.addstr(r, 0, label_text[: w - 1], attr)
                except curses.error:
                    pass
                if descriptions and i < len(descriptions) and LABEL_WIDTH < w - 1:
                    desc = descriptions[i][: w - LABEL_WIDTH - 1]
                    try:
                        stdscr.addstr(r, LABEL_WIDTH, desc, curses.A_DIM)
                    except curses.error:
                        pass
            row_pos = menu_start + n + 1
            # Status line (dim): from snapshot_getter if set, else status_getter
            if row_pos < h - 2:
                try:
                    if snapshot_getter:
                        snap = snapshot_getter()
                        lock = (snap.get("lock_status") or "-").strip()
                        enabled = bool(snap.get("presence_enabled", False))
                        running = bool(snap.get("presence_running", False))
                        pres = "OFF"
                        if enabled:
                            pres = "ON (running)" if running else "ON (stopped)"
                        log_ts = snap.get("last_log_ts") or "-"
                        status = f"Durum: {lock} | Presence: {pres} | Log: {log_ts}"[: w - 1]
                    elif status_getter:
                        status = status_getter()[: w - 1]
                    else:
                        status = ""
                    if status:
                        stdscr.addstr(row_pos, 0, status, curses.A_DIM)
                except (curses.error, Exception):
                    pass
            # Hint (bottom)
            if h > 1:
                try:
                    stdscr.addstr(h - 1, 0, hint[: w - 1], curses.A_DIM)
                except curses.error:
                    pass
            stdscr.refresh()

        while True:
            draw()
            key = stdscr.getch()
            if key in (curses.KEY_UP, ord("k")) and n > 0:
                idx = (idx - 1) % n
            elif key in (curses.KEY_DOWN, ord("j")) and n > 0:
                idx = (idx + 1) % n
            elif key in (ord("\n"), ord("\r"), curses.KEY_ENTER):
                _, cb = items[idx]
                if cb is None:
                    break
                if log_path is not None and log_item_index is not None and idx == log_item_index:
                    _run_log_viewer(stdscr, log_path)
                    continue
                try:
                    curses.endwin()
                except Exception:
                    pass
                try:
                    cb()
                except Exception:
                    pass
                try:
                    stdscr.refresh()
                    stdscr.clear()
                except Exception:
                    pass
            elif key in (ord("q"), ord("Q")):
                break

    try:
        curses.wrapper(main)
    except Exception:
        raise


def tui_available() -> bool:
    return curses is not None
