"""Tests for Lumos system identity and state injection in model_client.

Verifies:
- Lumos identifies as Lumos (not ChatGPT) in the system prompt
- Runtime state (mode, presence, consent, lock) is injectable into prompt construction
- Turkish is the default language in the prompt
- The combined prompt (system + user) is used in the OpenAI path when online
"""
import os
import unittest
from unittest.mock import MagicMock, patch


class TestLumosModelClientIdentity(unittest.TestCase):
    """Lumos identity and state injection in model_client."""

    def test_lumos_system_prompt_template_identifies_as_lumos(self):
        """System prompt template must identify the assistant as Lumos."""
        from engine.model_client import ModelClient

        template = ModelClient._LUMOS_SYSTEM_PROMPT_TEMPLATE
        self.assertIn("You are Lumos", template)
        self.assertIn("Lumos is a local AI system", template)
        self.assertIn("Lumos Core", template)

    def test_lumos_system_prompt_template_anti_chatgpt(self):
        """System prompt must explicitly reject ChatGPT identity (anti-drift)."""
        from engine.model_client import ModelClient

        template = ModelClient._LUMOS_SYSTEM_PROMPT_TEMPLATE
        self.assertIn("NOT ChatGPT", template)
        self.assertIn("Do NOT identify yourself as ChatGPT", template)
        self.assertIn("Do not mention ChatGPT", template)
        self.assertIn("Reply as Lumos", template)

    def test_lumos_system_prompt_template_turkish_default(self):
        """Default language in the prompt must be Turkish."""
        from engine.model_client import ModelClient

        template = ModelClient._LUMOS_SYSTEM_PROMPT_TEMPLATE
        self.assertIn("Turkish", template)

    def test_lumos_system_prompt_template_has_state_placeholders(self):
        """Template must have placeholders for runtime state injection."""
        from engine.model_client import ModelClient

        template = ModelClient._LUMOS_SYSTEM_PROMPT_TEMPLATE
        self.assertIn("{mode}", template)
        self.assertIn("{presence}", template)
        self.assertIn("{consent}", template)
        self.assertIn("{lock}", template)

    def test_state_injection_into_prompt_construction(self):
        """Runtime state values must be injected into the built system prompt."""
        from engine.model_client import ModelClient

        template = ModelClient._LUMOS_SYSTEM_PROMPT_TEMPLATE
        built = template.format(
            mode="online",
            presence="enabled",
            consent="ok",
            lock="unlocked",
        )
        self.assertIn("Mode: online", built)
        self.assertIn("Presence: enabled", built)
        self.assertIn("Consent: ok", built)
        self.assertIn("Lock: unlocked", built)

    def test_generate_uses_combined_prompt_when_openai_available(self):
        """When OPENAI_API_KEY is set, generate() must send system prompt + user prompt to the API."""
        from engine.model_client import ModelClient

        captured_input = None

        def fake_create(*, model=None, input=None, **kwargs):
            nonlocal captured_input
            captured_input = input
            resp = MagicMock()
            resp.output_text = "Lumos yanıtı."
            resp.output = None
            return resp

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "LUMOS_SERVER_SIM": "0"}):
            client = ModelClient()
            with patch.object(client, "_openai_key", "sk-test"):
                with patch("openai.OpenAI") as mock_openai_class:
                    mock_client = MagicMock()
                    mock_client.responses.create = fake_create
                    mock_openai_class.return_value = mock_client
                    out = client.generate(
                        "Merhaba",
                        mode="online",
                        presence="enabled",
                        consent="ok",
                        lock="unlocked",
                    )
        self.assertEqual(out, "Lumos yanıtı.")
        self.assertIsNotNone(captured_input)
        self.assertIn("You are Lumos", captured_input)
        self.assertIn("Mode: online", captured_input)
        self.assertIn("Presence: enabled", captured_input)
        self.assertIn("Consent: ok", captured_input)
        self.assertIn("Lock: unlocked", captured_input)
        self.assertIn("User: ", captured_input)
        self.assertIn("Merhaba", captured_input)

    def test_generate_fallback_when_no_openai_key(self):
        """When OPENAI_API_KEY is not set, generate() returns fallback without calling API."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "LUMOS_SERVER_SIM": "0"}, clear=False):
            from engine.model_client import ModelClient

            client = ModelClient()
            out = client.generate("test")
        self.assertEqual(out, "Yanındayım.")

    def test_online_engine_process_passes_state_to_generate(self):
        """OnlineEngineV1.process() must accept state kwargs and pass them to client.generate()."""
        from engine.online_engine import OnlineEngineV1

        captured_kw = None

        def capture_generate(prompt, *, mode="—", presence="—", consent="—", lock="—"):
            nonlocal captured_kw
            captured_kw = {"mode": mode, "presence": presence, "consent": consent, "lock": lock}
            return "Mock yanıt."

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "LUMOS_SERVER_SIM": "0"}):
            engine = OnlineEngineV1()
            engine.signer = None  # force direct OpenAI path
            engine.client.generate = capture_generate
            engine.process(
                "selam",
                short_context="",
                mode="online",
                presence="enabled",
                consent="ok",
                lock="unlocked",
            )
        self.assertIsNotNone(captured_kw)
        self.assertEqual(captured_kw["mode"], "online")
        self.assertEqual(captured_kw["presence"], "enabled")
        self.assertEqual(captured_kw["consent"], "ok")
        self.assertEqual(captured_kw["lock"], "unlocked")
