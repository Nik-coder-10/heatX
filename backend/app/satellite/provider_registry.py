"""Provider registry with auto-discovery and factory pattern.

New providers can be added by:
1. Creating a new module in ``app.satellite.providers``
2. Implementing ``BaseSatelliteProvider``
3. The registry auto-discovers via the ``__init__`` exports
"""

import importlib
import logging
import pkgutil
from typing import Any

from app.satellite.base_provider import BaseSatelliteProvider
from app.satellite.exceptions import ProviderNotFoundError

logger = logging.getLogger("app.satellite.registry")


class ProviderRegistry:
    """Registry that discovers, stores, and provides satellite providers.

    Usage::

        registry = ProviderRegistry()
        registry.discover()
        sentinel = registry.get("sentinel_2")
        for provider in registry.list_providers():
            logger.info("Discovered provider: %s", provider.provider_id)
    """

    def __init__(self) -> None:
        self._providers: dict[str, BaseSatelliteProvider] = {}
        self._discovered = False

    def discover(self, force: bool = False) -> None:
        """Auto-discover all provider implementations.

        Scans the ``app.satellite.providers`` package for modules
        that export a ``register`` attribute pointing to an
        ``BaseSatelliteProvider`` subclass.
        """
        if self._discovered and not force:
            return

        package = importlib.import_module("app.satellite.providers")
        for _finder, module_name, _ispkg in pkgutil.iter_modules(
            package.__path__, prefix=f"{package.__name__}."
        ):
            try:
                mod = importlib.import_module(module_name)
                provider_cls: type[BaseSatelliteProvider] | None = None

                if hasattr(mod, "register"):
                    candidate = getattr(mod, "register")
                    if isinstance(candidate, type) and issubclass(candidate, BaseSatelliteProvider):
                        provider_cls = candidate

                if provider_cls is None:
                    for attr_name in dir(mod):
                        attr = getattr(mod, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, BaseSatelliteProvider)
                            and attr is not BaseSatelliteProvider
                        ):
                            provider_cls = attr
                            break

                if provider_cls is not None:
                    instance = provider_cls()
                    pid = instance.provider_id
                    if pid in self._providers:
                        logger.warning("Provider '%s' already registered; skipping duplicate", pid)
                        continue
                    self._providers[pid] = instance
                    logger.info(
                        "Discovered provider '%s' (%s)", pid, provider_cls.__name__
                    )
                else:
                    logger.debug("No provider found in module '%s'", module_name)

            except Exception as exc:
                logger.warning("Failed to load provider module '%s': %s", module_name, exc)

        self._discovered = True

    def register(self, provider: BaseSatelliteProvider) -> None:
        """Manually register a provider instance."""
        pid = provider.provider_id
        if pid in self._providers:
            logger.warning("Provider '%s' already registered; overwriting", pid)
        self._providers[pid] = provider
        logger.info("Manually registered provider '%s'", pid)

    def get(self, provider_id: str) -> BaseSatelliteProvider:
        """Get a provider by its identifier.

        Raises:
            ProviderNotFoundError: If provider is not found.
        """
        if not self._discovered:
            self.discover()
        provider = self._providers.get(provider_id)
        if provider is None:
            raise ProviderNotFoundError(
                f"Provider '{provider_id}' not found. "
                f"Available: {', '.join(sorted(self._providers))}"
            )
        return provider

    def list_providers(self) -> list[BaseSatelliteProvider]:
        """Return all registered provider instances."""
        if not self._discovered:
            self.discover()
        return list(self._providers.values())

    def list_provider_ids(self) -> list[str]:
        """Return all registered provider identifiers."""
        if not self._discovered:
            self.discover()
        return sorted(self._providers.keys())

    def get_capabilities(self, provider_id: str) -> Any:
        """Return the capabilities descriptor for a provider."""
        return self.get(provider_id).capabilities

    def list_capabilities(self) -> dict[str, Any]:
        """Return capabilities for all registered providers."""
        return {
            pid: p.capabilities
            for pid, p in self._providers.items()
        }


_default_registry: ProviderRegistry | None = None


def get_registry() -> ProviderRegistry:
    """Return the application-global provider registry singleton."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ProviderRegistry()
        _default_registry.discover()
    return _default_registry
