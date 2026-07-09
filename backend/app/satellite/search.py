"""Satellite search orchestrator — combines provider search, caching, ranking.

Searches across all registered providers by:
- Bounding box
- Polygon AOI (GeoJSON)
- City name (uses shared utils if available)
- Date range
- Cloud cover %
- Resolution
- Mission
- Band availability
"""

import logging
from collections.abc import Sequence
from datetime import date, datetime, timezone
from typing import Any

from app.satellite.cache import SatelliteCache
from app.satellite.exceptions import InvalidSearchParameterError, SearchError
from app.satellite.provider_registry import ProviderRegistry

logger = logging.getLogger("app.satellite.search")

_CITY_BBOX: dict[str, list[float]] = {
    "bangalore": [77.4, 12.8, 77.8, 13.1],
    "mumbai": [72.7, 18.9, 73.0, 19.3],
    "delhi": [77.0, 28.4, 77.4, 28.8],
    "chennai": [80.1, 12.9, 80.3, 13.2],
    "kolkata": [88.2, 22.4, 88.5, 22.7],
    "hyderabad": [78.3, 17.3, 78.6, 17.5],
    "pune": [73.7, 18.4, 73.9, 18.6],
    "ahmedabad": [72.5, 22.9, 72.7, 23.1],
}


class SatelliteSearch:
    """Orchestrates satellite image search across all registered providers.

    Args:
        registry: Provider registry instance.
        cache: Optional cache for search results.
    """

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        cache: SatelliteCache | None = None,
    ) -> None:
        from app.satellite.provider_registry import get_registry

        self.registry = registry or get_registry()
        self.cache = cache or SatelliteCache()

    def search(
        self,
        bbox: list[float] | None = None,
        polygon: dict | None = None,
        city: str | None = None,
        date_from: date | str | None = None,
        date_to: date | str | None = None,
        max_cloud_cover: float | None = None,
        resolution: float | None = None,
        missions: list[str] | None = None,
        bands: list[str] | None = None,
        providers: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "acquisition_date",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        """Search for satellite imagery across multiple providers.

        Args:
            bbox: [min_lon, min_lat, max_lon, max_lat].
            polygon: GeoJSON Polygon dict.
            city: City name to resolve to a bounding box.
            date_from: Start acquisition date.
            date_to: End acquisition date.
            max_cloud_cover: Maximum cloud cover %.
            resolution: Max ground resolution in meters.
            missions: Filter by mission names.
            bands: Required spectral bands.
            providers: Provider IDs to search (None = all).
            limit: Max results per provider.
            offset: Pagination offset.
            sort_by: Sort field.
            sort_order: 'asc' or 'desc'.

        Returns:
            Dict with keys: results (list), total (int), providers_searched (list).
        """
        if bbox is None and polygon is None and city is None:
            raise InvalidSearchParameterError(
                "At least one of 'bbox', 'polygon', or 'city' is required"
            )

        if bbox and not self._validate_bbox(bbox):
            raise InvalidSearchParameterError(
                f"Invalid bounding box: {bbox}. "
                f"Expected [min_lon, min_lat, max_lon, max_lat]"
            )

        resolved_bbox = bbox
        if city:
            city_lower = city.strip().lower()
            resolved_bbox = _CITY_BBOX.get(city_lower)
            if resolved_bbox is None:
                logger.warning("Unknown city '%s', searching without location", city)
            else:
                logger.info("Resolved city '%s' to bbox %s", city, resolved_bbox)

        final_bbox = resolved_bbox or bbox

        date_from_dt = self._parse_date(date_from) if date_from else None
        date_to_dt = self._parse_date(date_to) if date_to else None

        cache_key = self._build_cache_key(
            final_bbox, polygon, city, date_from_dt, date_to_dt,
            max_cloud_cover, resolution, missions, bands, providers,
            limit, offset, sort_by, sort_order,
        )

        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        provider_ids = providers if providers else self.registry.list_provider_ids()
        all_results: list[dict] = []
        searched: list[str] = []

        for pid in provider_ids:
            try:
                provider = self.registry.get(pid)
            except Exception as exc:
                logger.warning("Skipping unavailable provider '%s': %s", pid, exc)
                continue

            if missions and not any(m in (provider.capabilities.missions or []) for m in missions):
                continue

            try:
                results = provider.search(
                    bbox=final_bbox,
                    polygon=polygon,
                    date_from=date_from_dt,
                    date_to=date_to_dt,
                    max_cloud_cover=max_cloud_cover,
                    resolution=resolution,
                    bands=bands,
                    limit=limit,
                    offset=offset,
                )
                all_results.extend(results)
                searched.append(pid)
                logger.debug(
                    "Provider '%s' returned %d results", pid, len(results)
                )
            except Exception as exc:
                logger.error("Provider '%s' search failed: %s", pid, exc)

        all_results = self._rank_results(
            all_results, sort_by=sort_by, sort_order=sort_order
        )

        if bands:
            all_results = [
                r for r in all_results
                if set(bands).issubset(set(r.get("bands", [])))
            ]

        result_payload = {
            "results": all_results[:limit],
            "total": len(all_results),
            "providers_searched": searched,
        }

        self.cache.set(cache_key, result_payload, ttl_seconds=300)

        logger.info(
            "Search complete: %d results from %d providers (cached=%s)",
            len(all_results), len(searched), cache_key[:16],
        )
        return result_payload

    def search_by_city(
        self,
        city: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Convenience method to search by city name."""
        return self.search(city=city, **kwargs)

    def list_providers(self) -> list[dict[str, Any]]:
        """Return a summary of all available providers and their capabilities."""
        caps = self.registry.list_capabilities()
        return [
            {
                "provider_id": pid,
                "name": c.display_name,
                "missions": c.missions,
                "bands": c.bands,
                "resolutions": c.resolutions,
                "products": c.products,
                "supports_polygon": c.supports_polygon_search,
                "supports_checksum": c.supports_checksum,
                "requires_api_key": c.requires_api_key,
            }
            for pid, c in caps.items()
        ]

    @staticmethod
    def _validate_bbox(bbox: list[float]) -> bool:
        if len(bbox) != 4:
            return False
        min_lon, min_lat, max_lon, max_lat = bbox
        return (
            -180 <= min_lon <= 180
            and -90 <= min_lat <= 90
            and -180 <= max_lon <= 180
            and -90 <= max_lat <= 90
            and min_lon < max_lon
            and min_lat < max_lat
        )

    @staticmethod
    def _rank_results(
        results: list[dict],
        sort_by: str = "acquisition_date",
        sort_order: str = "desc",
    ) -> list[dict]:
        """Sort search results by the given field."""
        reverse = sort_order.lower() == "desc"

        sort_key_map = {
            "acquisition_date": lambda r: r.get("acquisition_date", ""),
            "cloud_cover": lambda r: r.get("cloud_cover", 100.0),
            "resolution": lambda r: r.get("resolution", 999.0),
            "size_bytes": lambda r: r.get("size_bytes", 0),
            "scene_id": lambda r: r.get("scene_id", ""),
        }

        key_fn = sort_key_map.get(sort_by, sort_key_map["acquisition_date"])
        return sorted(results, key=key_fn, reverse=reverse)

    @staticmethod
    def _build_cache_key(*args: Any) -> str:
        """Build a deterministic cache key from search parameters."""
        parts = []
        for arg in args:
            if arg is None:
                parts.append("None")
            elif isinstance(arg, (list, tuple)):
                parts.append(",".join(str(x) for x in arg))
            elif isinstance(arg, dict):
                parts.append(str(sorted(arg.items())))
            elif isinstance(arg, (datetime, date)):
                parts.append(arg.isoformat())
            else:
                parts.append(str(arg))
        raw = "|".join(parts)
        import hashlib
        return "search:" + hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def _parse_date(value: date | str) -> date:
        if isinstance(value, date):
            return value
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                dt = datetime.strptime(str(value), fmt)
                return dt.date()
            except ValueError:
                continue
        raise InvalidSearchParameterError(f"Cannot parse date: '{value}'")
