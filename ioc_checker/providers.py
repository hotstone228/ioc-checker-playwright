"""Provider management module."""

from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, AsyncIterator
import logging

from . import virustotal, kaspersky

logger = logging.getLogger(__name__)


@dataclass
class Provider:
    """Configuration for a reputation provider."""

    name: str
    requires_token: bool
    context_factory: Callable[..., AsyncIterator[Any]]
    fetcher: Callable[[str, Any], Awaitable[Dict[str, Any]]]


PROVIDERS: Dict[str, Provider] = {
    "virustotal": Provider(
        name="virustotal",
        requires_token=False,
        context_factory=virustotal.playwright_browser,
        fetcher=virustotal.fetch_ioc_info,
    ),
    "kaspersky": Provider(
        name="kaspersky",
        requires_token=True,
        context_factory=kaspersky.get_context,
        fetcher=kaspersky.fetch_ioc_info,
    ),
}


def get_provider(name: str) -> Provider | None:
    """Return provider configuration by name."""
    return PROVIDERS.get(name)


def requires_token(name: str) -> bool:
    """Whether the provider requires a token for requests."""
    provider = get_provider(name)
    return bool(provider and provider.requires_token)


async def init_contexts(names: list[str]) -> tuple[Dict[str, Any], AsyncExitStack]:
    """Initialise contexts for all non-token providers.

    Returns a mapping of provider name to context and the AsyncExitStack used to
    manage them which must be closed by the caller.
    """
    stack = AsyncExitStack()
    contexts: Dict[str, Any] = {}
    for name in names:
        provider = get_provider(name)
        if not provider:
            logger.warning("Unknown provider %s configured", name)
            continue
        if not provider.requires_token:
            ctx = await stack.enter_async_context(provider.context_factory())
            contexts[name] = ctx
    return contexts, stack


async def fetch_ioc(
    service: str,
    ioc: str,
    token: str | None,
    contexts: Dict[str, Any],
) -> Dict[str, Any]:
    """Fetch IOC information using the appropriate provider."""
    provider = get_provider(service)
    if not provider:
        raise ValueError(f"unsupported service {service}")
    if provider.requires_token:
        if not token:
            raise ValueError("API token required")
        async with provider.context_factory(token) as ctx:
            return await provider.fetcher(ioc, ctx)
    context = contexts.get(service)
    if context is None:
        raise ValueError(f"no context for service {service}")
    return await provider.fetcher(ioc, context)
