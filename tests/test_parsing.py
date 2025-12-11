# tests/test_parsing.py

import asyncio
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from Source import parsing


class TestParsing(unittest.TestCase):
    def test_try_parse_coordinates_valid_space(self):
        lat, lon = parsing._try_parse_coordinates("55.7558 37.6173")
        self.assertAlmostEqual(lat, 55.7558)
        self.assertAlmostEqual(lon, 37.6173)

    def test_try_parse_coordinates_valid_comma(self):
        lat, lon = parsing._try_parse_coordinates("55.7558, 37.6173")
        self.assertAlmostEqual(lat, 55.7558)
        self.assertAlmostEqual(lon, 37.6173)

    def test_try_parse_coordinates_invalid_text(self):
        self.assertIsNone(parsing._try_parse_coordinates("москва"))
        self.assertIsNone(parsing._try_parse_coordinates("some trash"))

    def test_sanitize_input(self):
        result = parsing.sanitize_input("  Москва, Тверская 10  ")
        self.assertEqual(result, "Москва, Тверская 10")

    def test_parse_output_address_success(self):
        async def run():
            calls = {}

            async def fake_add_new_address(
                    input_query,
                    full_address,
                    lat,
                    lon
                    ):
                calls["input_query"] = input_query
                calls["full_address"] = full_address
                calls["lat"] = lat
                calls["lon"] = lon

            original_add = parsing.add_new_address
            parsing.add_new_address = fake_add_new_address

            output = {
                "lat": "56.7928003",
                "lon": "60.6165292",
                "address": {
                    "state": "Свердловская область",
                    "city": "Екатеринбург",
                    "road": "Родонитовая улица",
                    "house_number": "1",
                    "postcode": "620089",
                    "country": "Россия",
                },
                "display_name": "1 Родонитовая улица, Екатеринбург, Россия",
            }

            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    await parsing.parse_output_address(
                        "Екатеринбург, Родонитовая 1", output
                    )
            finally:
                parsing.add_new_address = original_add

            out = buf.getvalue().strip()

            self.assertTrue(out.startswith("Полный адрес:"))
            self.assertIn("Свердловская область", out)
            self.assertIn("Екатеринбург", out)
            self.assertIn("Родонитовая", out)
            self.assertIn("620089", out)
            self.assertIn("56.7928003", out)
            self.assertIn("60.6165292", out)

            self.assertEqual(
                calls["input_query"],
                "Екатеринбург, Родонитовая 1"
                )
            self.assertIn("Екатеринбург", calls["full_address"])

        asyncio.run(run())


class TestParsingExtra(unittest.TestCase):
    def test_contains_cyrillic_true_false(self):
        self.assertTrue(parsing._contains_cyrillic("Екатеринбург"))
        self.assertFalse(parsing._contains_cyrillic("Moscow123"))

    def test_build_normalized_string_empty(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            res = parsing._build_normalized_string({})
        out = buf.getvalue()
        self.assertIsNone(res)
        self.assertIn("пустой результат", out)

    def test_build_normalized_string_success(self):
        cleaned = {
            "street": "Родонитовая",
            "house": "1",
            "city": "Екатеринбург",
            "region": "Свердловская область",
            "country": "Россия",
        }
        res = parsing._build_normalized_string(cleaned)
        self.assertEqual(
            res,
            "Родонитовая 1 Екатеринбург Свердловская область Россия",
        )

    def test_clean_with_dadata_error(self):
        def boom(*_args, **_kwargs):
            raise RuntimeError("упс")

        with patch("Source.parsing._client") as client:
            client.clean = boom
            buf = io.StringIO()
            with redirect_stdout(buf):
                res = parsing._clean_with_dadata("Екб")
            out = buf.getvalue()
            self.assertIsNone(res)
            self.assertIn("Не удалось нормализовать адрес", out)

    def test_clean_with_dadata_success(self):
        fake_result = {"foo": "bar"}

        class DummyClient:
            def clean(self, *_args, **_kwargs):
                return fake_result

        with patch("Source.parsing._client", DummyClient()):
            res = parsing._clean_with_dadata("Екатеринбург, Белинского 86")
        self.assertEqual(res, fake_result)

    def test_normalize_free_text_failure(self):
        def fake_clean(_addr: str):
            return None

        with patch("Source.parsing._clean_with_dadata", fake_clean):
            res = parsing._normalize_free_text("Екб, Белинского 86")
        self.assertIsNone(res)

    def test_normalize_free_text_success(self):
        def fake_clean(_addr: str):
            return {
                "street": "Белинского",
                "house": "86",
                "city": "Екатеринбург",
                "region": "Свердловская область",
                "country": "Россия",
            }

        with patch("Source.parsing._clean_with_dadata", fake_clean):
            res = parsing._normalize_free_text("Екб, Белинского 86")

        self.assertEqual(
            res,
            "Белинского 86 Екатеринбург Свердловская область Россия",
        )

    def test_parse_output_address_empty_output(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            asyncio.run(parsing.parse_output_address("что-то", {}))
        out = buf.getvalue()
        self.assertIn("Пустой ответ от сервера геокодирования", out)

    def test_parse_output_address_add_new_address_error(self):
        output = {
            "lat": "56.79",
            "lon": "60.61",
            "address": {
                "state": "Свердловская область",
                "city": "Екатеринбург",
                "road": "Родонитовая улица",
                "house_number": "1",
                "postcode": "620089",
                "country": "Россия",
            },
        }

        async def bad_add(*_args, **_kwargs):
            raise RuntimeError("база упала")

        buf = io.StringIO()
        with redirect_stdout(buf):
            with patch("Source.parsing.add_new_address", bad_add):
                asyncio.run(
                    parsing.parse_output_address(
                        "Екатеринбург, Родонитовая 1",
                        output,
                    )
                )
        out = buf.getvalue()
        self.assertIn("Не удалось сохранить адрес", out)
        self.assertIn("Полный адрес:", out)

    def test_parse_output_address_house_only(self):
        output = {
            "lat": "56.79",
            "lon": "60.61",
            "address": {
                "state": "Свердловская область",
                "city": "Екатеринбург",
                "house_number": "1",
                "postcode": "620089",
                "country": "Россия",
            },
        }

        buf = io.StringIO()
        with redirect_stdout(buf):
            asyncio.run(
                parsing.parse_output_address(
                    "Екатеринбург, дом 1",
                    output,
                )
            )
        out = buf.getvalue()
        self.assertIn("Свердловская область", out)
        self.assertIn("Екатеринбург", out)
        self.assertIn("1", out)
        self.assertIn("620089", out)
        self.assertIn("56.79", out)
        self.assertIn("60.61", out)

    def test_parse_output_address_country_empty_and_not_russia(self):
        output = {
            "lat": "48.8566",
            "lon": "2.3522",
            "address": {
                "city": "Paris",
            },
            "display_name": "Paris, France",
        }

        buf = io.StringIO()
        with redirect_stdout(buf):
            asyncio.run(
                parsing.parse_output_address(
                    "Париж",
                    output,
                )
            )
        out = buf.getvalue()
        self.assertIn("вне пределов России", out)

    def test_sanitize_input_nonempty_and_empty(self):
        self.assertEqual(parsing.sanitize_input("  тест  "), "тест")
        self.assertIsNone(parsing.sanitize_input("   "))

    def test_try_parse_coordinates_invalid_variants(self):
        self.assertIsNone(parsing._try_parse_coordinates("1 2 3"))
        self.assertIsNone(parsing._try_parse_coordinates("a b"))
        self.assertIsNone(parsing._try_parse_coordinates("100 50"))

    def test_handle_free_query_empty(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            asyncio.run(parsing.handle_free_query("   "))
        out = buf.getvalue()
        self.assertIn("Пустой запрос", out)

    def test_handle_free_query_no_cyrillic(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            asyncio.run(parsing.handle_free_query("abc 123"))
        out = buf.getvalue()
        self.assertIn("Некорректный ввод", out)

    def test_handle_free_query_too_short(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            asyncio.run(parsing.handle_free_query("Москва"))
        out = buf.getvalue()
        self.assertIn("Слишком короткий адрес", out)

    def test_handle_free_query_normalize_fails(self):
        def fake_normalize(_text: str):
            return None

        async def run():
            with patch("Source.parsing._normalize_free_text", fake_normalize):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    await parsing.handle_free_query(
                        "Екатеринбург, Белинского 86"
                    )
                out = buf.getvalue()
                self.assertIn("Не удалось распознать адрес", out)

        asyncio.run(run())

    def test_handle_free_query_coords_path(self):
        calls = {}

        async def fake_send_request(text: str):
            calls["query"] = text

        async def run():
            with patch(
                "Source.parsing.response.send_request",
                fake_send_request
                ):
                await parsing.handle_free_query("55.75, 37.61")

        asyncio.run(run())
        self.assertEqual(calls.get("query"), "55.75 37.61")

    def test_handle_free_query_normalized_success(self):

        def fake_normalize(_text: str) -> str:
            return "Екатеринбург, Родонитовая 1"

        calls = {}

        async def fake_send_request(text: str):
            calls["query"] = text

        async def run():
            with patch(
                "Source.parsing._normalize_free_text",
                fake_normalize), \
                 patch(
                     "Source.parsing.response.send_request",
                     fake_send_request
                     ):
                await parsing.handle_free_query("что-то там")

        asyncio.run(run())
        self.assertEqual(calls.get("query"), "Екатеринбург, Родонитовая 1")


if __name__ == "__main__":
    unittest.main()
