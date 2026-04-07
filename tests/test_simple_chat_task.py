"""simple_chat_task: extract_task + run_task."""

from __future__ import annotations

import unittest
from pathlib import Path

from core.simple_chat_task import extract_task, run_task


class SimpleChatTaskTests(unittest.TestCase):
    def test_extract_py_create(self) -> None:
        t = extract_task("test.py oluştur içine print yaz")
        self.assertIsNotNone(t)
        assert t is not None
        self.assertEqual(t["action"], "create_file")
        self.assertEqual(t["input"]["filename"], "test.py")

    def test_extract_none_without_py(self) -> None:
        self.assertIsNone(extract_task("sadece oluştur"))

    def test_run_task_returns_ok(self) -> None:
        self.assertEqual(run_task({}, repo_root=None), "OK")
        p = Path("/Users/candasoz/WORK_2026/lumos-core/test.py")
        self.assertEqual(p.read_text(encoding="utf-8"), "print('hello')")


if __name__ == "__main__":
    unittest.main()
