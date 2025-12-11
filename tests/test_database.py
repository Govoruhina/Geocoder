# tests/test_database.py

import asyncio
import unittest
import uuid

from Source.database import models
from Source.database import requests as db_requests


class TestDatabase(unittest.TestCase):
    def test_init_db_and_add_get(self):
        async def run():
            await models.init_db()

            await db_requests.add_new_address(
                "тестовый запрос",
                "Тестовый полный адрес",
                1.23,
                4.56,
            )

            obj = await db_requests.return_address_if_exist("тестовый запрос")
            self.assertIsNotNone(obj)
            self.assertEqual(obj.full_address, "Тестовый полный адрес")
            self.assertAlmostEqual(obj.latitude, 1.23)
            self.assertAlmostEqual(obj.longitude, 4.56)

        asyncio.run(run())

    def test_return_address_if_not_exist(self):
        async def run():
            await models.init_db()
            obj = await db_requests.return_address_if_exist(
                "неизвестный запрос"
                )
            self.assertIsNone(obj)
        asyncio.run(run())


class TestDatabaseExtra(unittest.TestCase):
    def test_address_dataclass_like(self):
        addr = models.Address(
            input_query="q",
            full_address="Адрес",
            latitude=1.23,
            longitude=4.56,
        )
        self.assertEqual(addr.input_query, "q")
        self.assertEqual(addr.full_address, "Адрес")
        self.assertAlmostEqual(addr.latitude, 1.23)
        self.assertAlmostEqual(addr.longitude, 4.56)

    def test_init_db_creates_tables(self):
        async def run():
            await models.init_db()
        asyncio.run(run())

    def test_add_and_get_address_roundtrip(self):
        async def run():
            await models.init_db()

            query = "тестовый запрос " + str(uuid.uuid4())

            await db_requests.add_new_address(
                query,
                "Тестовый полный адрес",
                10.0,
                20.0,
            )

            obj = await db_requests.return_address_if_exist(query)
            self.assertIsNotNone(obj)
            if obj is not None:
                self.assertEqual(obj.input_query, query)
                self.assertEqual(obj.full_address, "Тестовый полный адрес")
                self.assertAlmostEqual(obj.latitude, 10.0)
                self.assertAlmostEqual(obj.longitude, 20.0)

        asyncio.run(run())

    def test_fallback_when_no_session(self):
        async def run():
            original_session = db_requests.async_session
            db_requests.async_session = None
            try:
                res = await db_requests.return_address_if_exist("что-то")
                self.assertIsNone(res)
                await db_requests.add_new_address("q", "a", 1.0, 2.0)
            finally:
                db_requests.async_session = original_session

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
