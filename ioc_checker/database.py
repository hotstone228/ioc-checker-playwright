from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, JSON, UniqueConstraint, select

from .config import settings

Base = declarative_base()


class Cache(Base):
    __tablename__ = "cache"

    id = Column(Integer, primary_key=True)
    ioc = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    response = Column(JSON, nullable=False)

    __table_args__ = (UniqueConstraint("ioc", "provider", name="uix_ioc_provider"),)


engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_cached_result(ioc: str, provider: str) -> dict | None:
    async with SessionLocal() as session:
        stmt = select(Cache).where(Cache.ioc == ioc, Cache.provider == provider)
        res = await session.execute(stmt)
        cache = res.scalars().first()
        if cache:
            return cache.response
    return None


async def cache_result(ioc: str, provider: str, response: dict) -> None:
    async with SessionLocal() as session:
        stmt = select(Cache).where(Cache.ioc == ioc, Cache.provider == provider)
        res = await session.execute(stmt)
        cache = res.scalars().first()
        if cache:
            cache.response = response
        else:
            cache = Cache(ioc=ioc, provider=provider, response=response)
            session.add(cache)
        await session.commit()
