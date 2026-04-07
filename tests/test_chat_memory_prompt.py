"""chat_memory_prompt: /chat öncesi kimlik + kullanıcı bağlamı."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.chat_memory_prompt import format_chat_prompt_prefix


class ChatMemoryPromptTests(unittest.TestCase):
    def test_always_includes_lumos_identity(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = format_chat_prompt_prefix(Path(d))
        self.assertIn("Lumos", p)
        self.assertIn("---", p)

    def test_loads_memory_and_preferences(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lumos = root / ".lumos"
            lumos.mkdir(parents=True)
            (lumos / "user_preferences.json").write_text(
                json.dumps({"display_name": "Ada", "summary": "Backend odaklı"}),
                encoding="utf-8",
            )
            (lumos / "user_memory.json").write_text(
                json.dumps({"text": "Vue yerine React tercih ediyor."}),
                encoding="utf-8",
            )
            p = format_chat_prompt_prefix(root)
        self.assertIn("Ada", p)
        self.assertIn("Backend", p)
        self.assertIn("React", p)


if __name__ == "__main__":
    unittest.main()
