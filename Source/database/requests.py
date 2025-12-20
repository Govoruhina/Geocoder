from typing import Optional

from Source.database.models import async_session, Address

try:
    from sqlalchemy import select, insert # type: ignore
except ModuleNotFoundError:
    select = None


async def _get_session():
    if async_session is None:
        return None
    return async_session()


async def return_address_if_exist(full_address: str) -> Optional[Address]:
    async with async_session() as session:
        stmt = select(Address).where(Address.full_address == full_address)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def add_new_address(input_query: str,
                          full_address: str,
                          lat: str,
                          lon: str) -> None:
    """Сохраняем только нормализованный адрес и координаты.

    input_query оставляем в сигнатуре для совместимости, но в БД не пишем.
    """
    async with async_session() as session:
        stmt = insert(Address).values(
            full_address=full_address,
            latitude=lat,
            longitude=lon,
        )
        await session.execute(stmt)
        await session.commit()
