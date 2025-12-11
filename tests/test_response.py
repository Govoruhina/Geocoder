# tests/test_response.py

import asyncio
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from Source import response


class TestResponse(unittest.TestCase):
    def test_print_json_result(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            response._print_json_result("запрос", "Адрес", 1.23, 4.56)
        out = buf.getvalue()
        data = json.loads(out)

        self.assertEqual(data["query"], "запрос")
        self.assertEqual(data["full_address"], "Адрес")
        self.assertAlmostEqual(data["latitude"], 1.23)
        self.assertAlmostEqual(data["longitude"], 4.56)

    def test_send_request_uses_cache(self):
        class Dummy:
            full_address = "Адрес из БД"
            latitude = 10.0
            longitude = 20.0

        async def fake_return_address_if_exist(query):
            return Dummy()

        def fake_requests_get(*args, **kwargs):
            raise AssertionError("HTTP не должен вызываться при наличии кэша")

        async def run():
            with patch(
                "Source.response.return_address_if_exist",
                fake_return_address_if_exist), \
                 patch("Source.response.requests.get",
                       fake_requests_get
                       ):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    await response.send_request("Екатеринбург, Родонитовая 1")
                out = buf.getvalue()
                data = json.loads(out)
                self.assertEqual(data["full_address"], "Адрес из БД")

        asyncio.run(run())

    def test_send_request_calls_parsing_when_not_cached(self):
        async def fake_return_address_if_exist(query):
            return None

        class DummyResp:
            ok = True

            def json(self):
                return [
                    {
                        "lat": "56.1",
                        "lon": "60.2",
                        "address": {
                            "state": "Свердловская область",
                            "city": "Екатеринбург",
                            "road": "Родонитовая улица",
                            "house_number": "1",
                            "postcode": "620089",
                            "country": "Россия",
                        },
                        "display_name":
                        "1 Родонитовая улица, Екатеринбург, Россия",
                    }
                ]

        def fake_requests_get(*args, **kwargs):
            return DummyResp()

        calls = {}

        async def fake_parse_output_address(input_address, output):
            calls["input_address"] = input_address
            calls["output"] = output

        async def run():
            with patch(
                "Source.response.return_address_if_exist",
                fake_return_address_if_exist), \
                 patch("Source.response.requests.get",
                       fake_requests_get
                       ), \
                 patch(
                     "Source.response.parsing.parse_output_address",
                     fake_parse_output_address
                     ):
                await response.send_request("Екатеринбург, Родонитовая 1")

        asyncio.run(run())
        self.assertEqual(calls["input_address"], "Екатеринбург, Родонитовая 1")
        self.assertEqual(calls["output"]["lat"], "56.1")


class TestResponseExtra(unittest.TestCase):
    def test_send_request_http_exception(self):
        async def run():
            async def fake_return_address_if_exist(query):
                return None

            def fake_get(*args, **kwargs):
                raise RuntimeError("network down")

            with patch(
                    "Source.response.return_address_if_exist",
                    fake_return_address_if_exist
                    ), \
                    patch("Source.response.requests.get", fake_get):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    await response.send_request("Екатеринбург, Белинского 86")
                out = buf.getvalue()
                self.assertIn(
                    "Ошибка при обращении к сервису геокодирования",
                    out
                    )

        asyncio.run(run())

    def test_send_request_http_not_ok(self):
        class DummyResp:
            ok = False
            status_code = 503

            def json(self):
                raise AssertionError(
                    "json() не должен вызываться при ok=False"
                    )

        async def run():
            async def fake_return_address_if_exist(query):
                return None

            def fake_get(*args, **kwargs):
                return DummyResp()

            with patch(
                    "Source.response.return_address_if_exist",
                    fake_return_address_if_exist
                    ), \
                    patch("Source.response.requests.get", fake_get):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    await response.send_request("Екатеринбург, Белинского 86")
                out = buf.getvalue()
                self.assertIn("HTTP 503", out)

        asyncio.run(run())

    def test_send_request_empty_payload(self):
        class DummyResp:
            ok = True

            def json(self):
                return []

        async def run():
            async def fake_return_address_if_exist(query):
                return None

            def fake_get(*args, **kwargs):
                return DummyResp()

            with patch(
                    "Source.response.return_address_if_exist",
                    fake_return_address_if_exist
                    ), \
                    patch("Source.response.requests.get", fake_get):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    await response.send_request("Екатеринбург")
                out = buf.getvalue()
                self.assertIn("ничего не найдено", out)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
