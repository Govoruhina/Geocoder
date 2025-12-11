# tests/test_main.py

import io
import unittest
from contextlib import redirect_stdout
import asyncio
import io
from unittest.mock import patch

from main import show_help
import main
import sys


class TestMain(unittest.TestCase):
    def test_show_help_prints_something(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            show_help()
        out = buf.getvalue()
        self.assertIn("Российский геокодер", out)
        self.assertIn("--help", out)


class TestMainExtra(unittest.TestCase):
    def test_handle_query_delegates_to_parsing(self):
        calls = {}

        async def fake_handle_free_query(text: str):
            calls["text"] = text

        async def run():
            with patch(
                    "main.parsing.handle_free_query",
                    fake_handle_free_query
                    ):
                await main.handle_query("адрес")

        asyncio.run(run())
        self.assertEqual(calls.get("text"), "адрес")

    def test_main_with_help_argument(self):
        async def run():
            with patch.object(sys, "argv", ["main.py", "--help"]):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    await main.main()
                out = buf.getvalue()
                self.assertIn("Российский геокодер", out)

        asyncio.run(run())

    def test_main_with_query_argument(self):
        calls = {}

        async def fake_handle_free_query(text: str):
            calls["text"] = text

        async def run():
            with patch.object(
                sys, "argv", ["main.py", "Екатеринбург, Родонитовая 1"]
                ), \
                 patch(
                     "main.parsing.handle_free_query",
                     fake_handle_free_query
                     ):

                async def fake_init_db():
                    return None

                with patch("main.init_db", fake_init_db):
                    await main.main()

        asyncio.run(run())
        self.assertEqual(calls.get("text"), "Екатеринбург, Родонитовая 1")

    def test_interactive_mode_help_and_exit(self):
        inputs = iter(["--help", "exit"])

        def fake_input(_prompt: str) -> str:
            return next(inputs)

        async def fake_handle_query(_text: str):
            return None

        async def run():
            with patch("builtins.input", fake_input), \
                 patch("main.handle_query", fake_handle_query):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    await main.interactive_mode()
                out = buf.getvalue()
                self.assertIn("Российский геокодер", out)
                self.assertIn("Введите 'exit' или 'выход' для завершения", out)
                self.assertIn("Завершение работы.", out)

        asyncio.run(run())

    def test_main_without_args_runs_interactive_mode(self):
        calls = {
            "interactive_called": False,
            "init_db_called": False,
        }

        async def fake_interactive_mode():
            calls["interactive_called"] = True

        async def fake_init_db():
            calls["init_db_called"] = True

        async def run():
            with patch.object(sys, "argv", ["main.py"]), \
                 patch("main.interactive_mode", fake_interactive_mode), \
                 patch("main.init_db", fake_init_db):
                await main.main()

        asyncio.run(run())

        self.assertTrue(calls["interactive_called"])
        self.assertTrue(calls["init_db_called"])

    def test_main_with_short_help_argument(self):
        async def run():
            with patch.object(sys, "argv", ["main.py", "-h"]):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    await main.main()
                out = buf.getvalue()
                self.assertIn("Российский геокодер", out)

        asyncio.run(run())

    def test_interactive_mode_query_then_exit(self):
        calls = {
            "query": None,
        }

        inputs = iter([
            "Екатеринбург, Белинского 86",
            "выход",
        ])

        def fake_input(_prompt: str) -> str:
            return next(inputs)

        async def fake_handle_query(text: str):
            calls["query"] = text

        async def run():
            with patch("builtins.input", fake_input), \
                 patch("main.handle_query", fake_handle_query):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    await main.interactive_mode()
                out = buf.getvalue()
                self.assertIn("exit' или 'выход' для завершения", out)

        asyncio.run(run())
        self.assertEqual(calls["query"], "Екатеринбург, Белинского 86")

    def test_ensure_dependencies_no_file(self):
        with patch("main.os.path.exists", return_value=False), \
             patch("main.subprocess.check_call") as mock_call:
            main.ensure_dependencies_installed("req.txt")
        mock_call.assert_not_called()

    def test_ensure_dependencies_success(self):
        with patch("main.os.path.exists", return_value=True), \
             patch("main.subprocess.check_call") as mock_call:
            main.ensure_dependencies_installed("req.txt")
        self.assertTrue(mock_call.called)

    def test_ensure_dependencies_install_error(self):
        with patch("main.os.path.exists", return_value=True), \
             patch(
                 "main.subprocess.check_call",
                 side_effect=RuntimeError("boom")
                 ):
            # просто не должно выбросить исключение
            main.ensure_dependencies_installed("req.txt")

    def test_main_with_exit_argument(self):
        calls = {
            "called": False,
        }

        async def fake_handle_query(_text: str):
            calls["called"] = True

        async def fake_init_db():
            return None

        async def run():
            with patch.object(sys, "argv", ["main.py", "exit"]), \
                 patch("main.handle_query", fake_handle_query), \
                 patch("main.init_db", fake_init_db):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    await main.main()
                out = buf.getvalue()
                self.assertIn("Завершение работы.", out)

        asyncio.run(run())
        self.assertFalse(calls["called"])

    def test_interactive_mode_keyboard_interrupt(self):

        def fake_input(_prompt: str) -> str:
            raise KeyboardInterrupt

        async def run():
            with patch("builtins.input", fake_input):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    await main.interactive_mode()
                out = buf.getvalue()
                self.assertIn("Завершение работы.", out)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
