from dataclasses import dataclass


@dataclass
class Context:
    message: str = ""
    online: bool = False
    confidence: float = 1.0
    user_is_child: bool = False
    short_context: str = ""
    memory_note_count: int = 0
    is_unlocked: bool = True
