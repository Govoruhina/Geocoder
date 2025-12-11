# tests/test_utils.py

import unittest

from Source.utils import _first_non_empty, build_address_from_components


class TestUtils(unittest.TestCase):
    def test_first_non_empty_found(self):
        data = {"city": "Екатеринбург", "town": "Деревня"}
        result = _first_non_empty(data, ("village", "city"))
        self.assertEqual(result, "Екатеринбург")

    def test_first_non_empty_none(self):
        data = {}
        result = _first_non_empty(data, ("a", "b"))
        self.assertIsNone(result)

    def test_build_address_full(self):
        address = {
            "state": "Свердловская область",
            "city": "Екатеринбург",
            "road": "Родонитовая улица",
            "house_number": "1",
            "postcode": "620089",
            "country": "Россия",
        }

        result = build_address_from_components(address)

        self.assertIn("Свердловская", result)
        self.assertIn("Екатеринбург", result)
        self.assertIn("Родонитовая", result)
        self.assertIn("620089", result)
        self.assertIn("Россия", result)

    def test_build_address_empty(self):
        self.assertIsNone(build_address_from_components({}))


if __name__ == "__main__":
    unittest.main()
