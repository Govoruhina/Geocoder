from typing import Optional

try:
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
    from sqlalchemy.ext.asyncio import (AsyncAttrs,
                                        async_sessionmaker,
                                        create_async_engine)
    from sqlalchemy import String, insert  # type: ignore

    DB_URL = "sqlite+aiosqlite:///db.sqlite3"

    engine = create_async_engine(DB_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    class Base(AsyncAttrs, DeclarativeBase):
        pass

    class Address(Base):
        __tablename__ = "addresses"

        id: Mapped[int] = mapped_column(primary_key=True)
        full_address: Mapped[str] = mapped_column(String, nullable=False)
        latitude: Mapped[str] = mapped_column(String, nullable=False)
        longitude: Mapped[str] = mapped_column(String, nullable=False)

    async def init_db() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

except ModuleNotFoundError:  # pragma: no cover
    engine = None
    async_session = None  # type: ignore[assignment]

    class Address:
        def __init__(
            self,
            input_query: Optional[str] = None,
            full_address: Optional[str] = None,
            latitude: Optional[float] = None,
            longitude: Optional[float] = None,
        ) -> None:
            self.input_query = input_query
            self.full_address = full_address
            self.latitude = latitude
            self.longitude = longitude

    async def init_db() -> None:  # type: ignore[empty-body]
        return None
