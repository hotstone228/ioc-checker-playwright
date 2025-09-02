import asyncio
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ioc_checker.virustotal import playwright_browser, fetch_ioc_info

NON_EXISTENT_HASH = "475F6E68E30D296766CC730B6C882653A5EB9A04031812FF0426D081F1FC86BD"
NON_EXISTENT_DOMAIN = "rambler.r"


def test_nonexistent_ioc_raises_value_error():
    async def run():
        async with playwright_browser() as ctx:
            with pytest.raises(ValueError):
                await fetch_ioc_info(NON_EXISTENT_HASH, ctx)
    asyncio.run(run())


def test_nonexistent_domain_raises_value_error():
    async def run():
        async with playwright_browser() as ctx:
            with pytest.raises(ValueError):
                await fetch_ioc_info(NON_EXISTENT_DOMAIN, ctx)
    asyncio.run(run())
