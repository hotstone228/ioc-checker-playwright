import asyncio
import importlib

from ioc_checker.config import settings


def test_cache_result_only_stores_200_and_404(tmp_path):
    settings.database_url = f"sqlite+aiosqlite:///{tmp_path/'test.db'}"
    import ioc_checker.database as database
    importlib.reload(database)

    async def run():
        await database.init_db()
        await database.cache_result("ioc1", "service", {"status_code": 200, "data": 1})
        assert await database.get_cached_result("ioc1", "service") == {"status_code": 200, "data": 1}

        await database.cache_result("ioc2", "service", {"status_code": 500})
        assert await database.get_cached_result("ioc2", "service") is None

        await database.cache_result("ioc3", "service", {"status_code": 404})
        assert await database.get_cached_result("ioc3", "service") == {"status_code": 404}

    asyncio.run(run())
