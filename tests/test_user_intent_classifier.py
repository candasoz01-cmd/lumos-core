"""user_intent_classifier: TASK | CHAT | HYBRID | UNCERTAIN kural katmanı."""

from __future__ import annotations

import unittest

from core.user_intent_classifier import (
    EXAMPLE_CASES,
    IntentClassification,
    classify_user_message_intent,
)


class UserIntentClassifierTests(unittest.TestCase):
    def test_example_cases_documented(self) -> None:
        for text, expected, _note in EXAMPLE_CASES:
            r = classify_user_message_intent(text)
            self.assertEqual(
                r.label,
                expected,
                msg=f"{text!r} -> {r.label} (want {expected})",
            )

    def test_task_clear_ops(self) -> None:
        self.assertEqual(classify_user_message_intent("fix the bug in login.py").label, "TASK")
        self.assertEqual(classify_user_message_intent("delete tmp/cache.json").label, "TASK")
        self.assertEqual(classify_user_message_intent("run all unit tests").label, "TASK")

    def test_chat_epistemic(self) -> None:
        self.assertEqual(
            classify_user_message_intent(
                "why does this pattern cause a deadlock?"
            ).label,
            "CHAT",
        )
        self.assertEqual(
            classify_user_message_intent("what would you prioritize here?").label,
            "CHAT",
        )

    def test_hybrid_english_clause(self) -> None:
        r = classify_user_message_intent(
            "I think this API is messy, please refactor the handler"
        )
        self.assertIn(r.label, ("HYBRID", "TASK"))

    def test_uncertain_tiny(self) -> None:
        r = classify_user_message_intent("hm")
        self.assertEqual(r.label, "UNCERTAIN")
        self.assertTrue(r.clarification_needed)

    def test_debug_returns_scores(self) -> None:
        r, dbg = classify_user_message_intent("hello", debug=True)
        self.assertIn("task_score", dbg)
        self.assertIn("chat_score", dbg)
        self.assertIn("force_hybrid", dbg)
        self.assertIsInstance(r, IntentClassification)

    def test_json_shape_fields(self) -> None:
        r = classify_user_message_intent("merhaba")
        d = {
            "label": r.label,
            "confidence": r.confidence,
            "reason": r.reason,
            "action_required": r.action_required,
            "clarification_needed": r.clarification_needed,
        }
        self.assertEqual(
            set(d.keys()),
            {
                "label",
                "confidence",
                "reason",
                "action_required",
                "clarification_needed",
            },
        )
        self.assertIsInstance(d["confidence"], float)


if __name__ == "__main__":
    unittest.main()
