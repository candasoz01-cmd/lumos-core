"""
Structured logging: logfmt(event, **fields) -> event=... key=val ...
None omitted; bool -> true/false; str with space quoted (inner quote escaped).
"""
from __future__ import annotations


def _format_value(v: object) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    s = str(v)
    if " " in s or '"' in s or "\\" in s:
        s = '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def logfmt(event: str, **fields: object) -> str:
    """Single line: event=<event> then sorted key=value; None omitted."""
    out = ["event=" + _format_value(event)]
    for k in sorted(fields.keys()):
        v = fields[k]
        if v is None:
            continue
        val_str = _format_value(v)
        if val_str == "":
            continue
        out.append(f"{k}={val_str}")
    return " ".join(out)
