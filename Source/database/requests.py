from typing import Optional

from Source.database.models import async_session, Address

try:
    from sqlalchemy import select  # type: ignore
except ModuleNotFoundError:
    select = None


async def _get_session():
    if async_session is None:
        return None
    return async_session()


async def return_address_if_exist(query: str) -> Optional[Address]:
    session = await _get_session()
    if session is None or select is None:
        return None

    async with session as s:
        result = await s.execute(select(Address)
                                 .where(Address.input_query == query)
                                 .limit(1))
        return result.scalar_one_or_none()


async def add_new_address(
        input_query: str,
        full_address: str,
        lat: float, lon: float
        ) -> None:
    session = await _get_session()
    if session is None:
        return

    async with session as s:
        async with s.begin():
            s.add(
                Address(
                    input_query=input_query,
                    full_address=full_address,
                    latitude=float(lat),
                    longitude=float(lon),
                )
            )
