# tests/test_parsing_handle.py

import asyncio
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from Source import parsing


class TestHandleFreeQuery(unittest.TestCase):
    def _run_and_capture(self, coro):
        buf = io.StringIO()
        with redirect_stdout(buf):
            asyncio.run(coro)
        return buf.getvalue()

    def test_empty_input(self):
        out = self._run_and_capture(parsing.handle_free_query("   "))
        self.assertIn("Пустой запрос", out)

    def test_latin_input(self):
        out = self._run_and_capture(parsing.handle_free_query("some trash"))
        self.assertIn("Некорректный ввод", out)

    def test_too_short_address(self):
        out = self._run_and_capture(parsing.handle_free_query("Москва"))
        self.assertIn("Слишком короткий адрес", out)

    def test_normalized_address_calls_send_request(self):
        def fake_normalize(text):
            return "Екатеринбург, Родонитовая 1"

        calls = {}

        async def fake_send_request(text):
            calls["query"] = text

        async def run():
            with patch(
                "Source.parsing._normalize_free_text",
                fake_normalize), \
                 patch(
                     "Source.parsing.response.send_request",
                     fake_send_request
                     ):
                await parsing.handle_free_query("Екатеринбург, Родонитовая 1")

        asyncio.run(run())
        self.assertEqual(calls.get("query"), "Екатеринбург, Родонитовая 1")


if __name__ == "__main__":
    unittest.main()
