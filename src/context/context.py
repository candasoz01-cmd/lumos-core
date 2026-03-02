from dataclasses import dataclass

@dataclass
class Context:
    message: str = ""
    online: bool = False
    confidence: float = 1.0
    user_is_child: bool = False
    short_context: str = ""
    lumos_id: str = ""
    unlocked: bool = False
