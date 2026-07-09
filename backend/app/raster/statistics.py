"""Raster statistics — min, max, mean, median, std, histogram, percentiles, NoData%."""

import logging
import math
from typing import Any, Optional

import numpy as np
import rasterio

from app.raster.exceptions import (
    CorruptedRasterError,
    RasterNotFoundError,
    RasterStatisticsError,
)
from app.raster.reader import _open_raster

logger = logging.getLogger("app.raster.statistics")

_WINDOW_SIZE = 1024


def _read_band_safe(path: str, band: int) -> np.ma.MaskedArray:
    with _open_raster(path) as src:
        if band < 1 or band > src.count:
            raise RasterStatisticsError(
                f"Band {band} out of range (1-{src.count}) for '{path}'"
            )
        return src.read(band, masked=True)


def _windowed_stat(path: str, band: int, stat_fn) -> Any:
    """Compute a statistic over a raster using windowed reads for memory safety."""
    with _open_raster(path) as src:
        if band < 1 or band > src.count:
            raise RasterStatisticsError(
                f"Band {band} out of range (1-{src.count}) for '{path}'"
            )

        accumulator = None
        from rasterio.windows import Window

        for col_off in range(0, src.width, _WINDOW_SIZE):
            for row_off in range(0, src.height, _WINDOW_SIZE):
                w = Window(
                    col_off, row_off,
                    min(_WINDOW_SIZE, src.width - col_off),
                    min(_WINDOW_SIZE, src.height - row_off),
                )
                block = src.read(band, window=w, masked=True)
                compressed = block.compressed()
                if len(compressed) == 0:
                    continue
                accumulator = stat_fn(accumulator, compressed)

        if accumulator is None:
            return None
        return accumulator


def _windowed_histogram(path, band, bins=256):
    """Compute histogram using windowed reads."""
    with _open_raster(path) as src:
        if band < 1 or band > src.count:
            raise RasterStatisticsError(
                f"Band {band} out of range (1-{src.count}) for '{path}'"
            )

        total_hist = None
        from rasterio.windows import Window

        for col_off in range(0, src.width, _WINDOW_SIZE):
            for row_off in range(0, src.height, _WINDOW_SIZE):
                w = Window(
                    col_off, row_off,
                    min(_WINDOW_SIZE, src.width - col_off),
                    min(_WINDOW_SIZE, src.height - row_off),
                )
                block = src.read(band, window=w, masked=True)
                compressed = block.compressed()
                if len(compressed) == 0:
                    continue
                hist, _ = np.histogram(compressed, bins=bins)
                if total_hist is None:
                    total_hist = hist.astype(np.int64)
                else:
                    total_hist += hist

        if total_hist is None:
            return None, None

        bin_edges = np.linspace(
            float(compressed.min()), float(compressed.max()), bins + 1
        )
        return total_hist.tolist(), bin_edges.tolist()


def compute_statistics(
    path: str,
    band: int = 1,
    approx: bool = True,
    windowed: bool = False,
) -> dict[str, Any]:
    """Compute basic statistics for a raster band.

    Args:
        path: Path to the raster file.
        band: 1-based band index.
        approx: If True, use overviews for faster approximate stats.
        windowed: If True, use windowed reads (memory-safe for large rasters).

    Returns:
        Dict with keys: min, max, mean, median, std, nodata_count, valid_count.
    """
    import os
    if not os.path.isfile(path):
        raise RasterNotFoundError(f"File not found: {path}")

    try:
        if windowed:
            return _compute_stats_windowed(path, band)

        with _open_raster(path) as src:
            if band < 1 or band > src.count:
                raise RasterStatisticsError(
                    f"Band {band} out of range (1-{src.count})"
                )

            if approx:
                data = src.read(band, masked=True, out_shape=(256, 256))
            else:
                data = src.read(band, masked=True)

            compressed = data.compressed()
            if len(compressed) == 0:
                return {
                    "band": band,
                    "min": None,
                    "max": None,
                    "mean": None,
                    "median": None,
                    "std": None,
                    "nodata_count": int(data.mask.sum()) if hasattr(data, "mask") else 0,
                    "total_count": data.size,
                    "valid_count": 0,
                }

            total_count = data.size
            nodata_count = int(np.ma.count_masked(data)) if isinstance(data, np.ma.MaskedArray) else 0

            return {
                "band": band,
                "min": float(compressed.min()),
                "max": float(compressed.max()),
                "mean": float(compressed.mean()),
                "median": float(np.median(compressed)),
                "std": float(compressed.std()),
                "nodata_count": nodata_count,
                "total_count": total_count,
                "valid_count": int(len(compressed)),
            }

    except RasterStatisticsError:
        raise
    except Exception as exc:
        raise RasterStatisticsError(
            f"Failed to compute statistics for '{path}' band {band}: {exc}"
        ) from exc


def _compute_stats_windowed(path: str, band: int) -> dict[str, Any]:
    """Compute statistics using windowed reads for memory safety."""
    with _open_raster(path) as src:
        if band < 1 or band > src.count:
            raise RasterStatisticsError(
                f"Band {band} out of range (1-{src.count})"
            )

        total_count = src.height * src.width
        nodata_count = 0
        valid_values = []
        from rasterio.windows import Window

        for col_off in range(0, src.width, _WINDOW_SIZE):
            for row_off in range(0, src.height, _WINDOW_SIZE):
                w = Window(
                    col_off, row_off,
                    min(_WINDOW_SIZE, src.width - col_off),
                    min(_WINDOW_SIZE, src.height - row_off),
                )
                block = src.read(band, window=w, masked=True)
                compressed = block.compressed()
                if len(compressed) == 0:
                    continue
                valid_values.append(compressed)

        if not valid_values:
            return {
                "band": band,
                "min": None,
                "max": None,
                "mean": None,
                "median": None,
                "std": None,
                "nodata_count": total_count,
                "total_count": total_count,
                "valid_count": 0,
            }

        all_values = np.concatenate(valid_values)
        return {
            "band": band,
            "min": float(all_values.min()),
            "max": float(all_values.max()),
            "mean": float(all_values.mean()),
            "median": float(np.median(all_values)),
            "std": float(all_values.std()),
            "nodata_count": int(nodata_count),
            "total_count": total_count,
            "valid_count": int(len(all_values)),
        }


def compute_histogram(
    path: str,
    band: int = 1,
    bins: int = 256,
    windowed: bool = False,
) -> dict[str, Any]:
    """Compute histogram for a raster band.

    Args:
        path: Path to the raster file.
        band: 1-based band index.
        bins: Number of histogram bins.
        windowed: If True, use windowed reads.

    Returns:
        Dict with keys: histogram (list of counts), bin_edges, band, bins.
    """
    import os
    if not os.path.isfile(path):
        raise RasterNotFoundError(f"File not found: {path}")

    try:
        if windowed:
            hist, bin_edges = _windowed_histogram(path, band, bins)
        else:
            with _open_raster(path) as src:
                if band < 1 or band > src.count:
                    raise RasterStatisticsError(
                        f"Band {band} out of range (1-{src.count})"
                    )
                data = src.read(band, masked=True)
                compressed = data.compressed()
                if len(compressed) == 0:
                    return {"band": band, "histogram": [], "bin_edges": [], "bins": bins}
                hist, bin_edges = np.histogram(compressed, bins=bins)

        return {
            "band": band,
            "histogram": hist if isinstance(hist, list) else hist.tolist(),
            "bin_edges": bin_edges if isinstance(bin_edges, list) else bin_edges.tolist(),
            "bins": bins,
        }

    except Exception as exc:
        raise RasterStatisticsError(
            f"Failed to compute histogram for '{path}' band {band}: {exc}"
        ) from exc


def compute_percentiles(
    path: str,
    band: int = 1,
    percentiles: Optional[list[float]] = None,
    windowed: bool = False,
) -> dict[str, Any]:
    """Compute specified percentiles for a raster band.

    Args:
        path: Path to the raster file.
        band: 1-based band index.
        percentiles: List of percentile values (0-100). Default: [2, 10, 25, 50, 75, 90, 98].
        windowed: If True, use windowed reads.

    Returns:
        Dict mapping percentile -> value.
    """
    if percentiles is None:
        percentiles = [2, 10, 25, 50, 75, 90, 98]

    import os
    if not os.path.isfile(path):
        raise RasterNotFoundError(f"File not found: {path}")

    try:
        if windowed:
            with _open_raster(path) as src:
                if band < 1 or band > src.count:
                    raise RasterStatisticsError(
                        f"Band {band} out of range (1-{src.count})"
                    )
                valid_values = []
                from rasterio.windows import Window
                for col_off in range(0, src.width, _WINDOW_SIZE):
                    for row_off in range(0, src.height, _WINDOW_SIZE):
                        w = Window(
                            col_off, row_off,
                            min(_WINDOW_SIZE, src.width - col_off),
                            min(_WINDOW_SIZE, src.height - row_off),
                        )
                        block = src.read(band, window=w, masked=True)
                        compressed = block.compressed()
                        if len(compressed) > 0:
                            valid_values.append(compressed)
                if not valid_values:
                    return {str(p): None for p in percentiles}
                all_values = np.concatenate(valid_values)
        else:
            data = _read_band_safe(path, band)
            compressed = data.compressed()
            if len(compressed) == 0:
                return {str(p): None for p in percentiles}
            all_values = compressed

        result = {}
        for p in percentiles:
            result[str(p)] = float(np.percentile(all_values, p))

        return result

    except Exception as exc:
        raise RasterStatisticsError(
            f"Failed to compute percentiles for '{path}' band {band}: {exc}"
        ) from exc


def compute_nodata_percentage(path: str, band: int = 1) -> dict[str, Any]:
    """Compute the percentage of NoData pixels in a raster band.

    Args:
        path: Path to the raster file.
        band: 1-based band index.

    Returns:
        Dict with keys: nodata_pct, nodata_count, total_count, band.
    """
    import os
    if not os.path.isfile(path):
        raise RasterNotFoundError(f"File not found: {path}")

    try:
        with _open_raster(path) as src:
            if band < 1 or band > src.count:
                raise RasterStatisticsError(
                    f"Band {band} out of range (1-{src.count})"
                )

            data = src.read(band, masked=True)
            total = data.size
            nodata = int(np.ma.count_masked(data))
            pct = (nodata / total * 100.0) if total > 0 else 0.0

            return {
                "band": band,
                "nodata_pct": round(pct, 4),
                "nodata_count": nodata,
                "total_count": total,
            }

    except Exception as exc:
        raise RasterStatisticsError(
            f"Failed to compute NoData %% for '{path}' band {band}: {exc}"
        ) from exc


def compute_all_statistics(
    path: str,
    approx: bool = True,
    windowed: bool = False,
) -> dict[str, Any]:
    """Compute all statistics for all bands in a raster.

    Args:
        path: Path to the raster file.
        approx: If True, use approximate stats via overviews.
        windowed: If True, use windowed reads.

    Returns:
        Dict with keys: bands (list of per-band stats), total_stats.
    """
    import os
    if not os.path.isfile(path):
        raise RasterNotFoundError(f"File not found: {path}")

    try:
        with _open_raster(path) as src:
            count = src.count

        per_band = []
        for i in range(1, count + 1):
            stats = compute_statistics(path, band=i, approx=approx, windowed=windowed)
            per_band.append(stats)

        valid_means = [b["mean"] for b in per_band if b["mean"] is not None]
        total_pixels = sum(b["total_count"] for b in per_band) if per_band else 0
        total_nodata = sum(b["nodata_count"] for b in per_band) if per_band else 0

        return {
            "bands": per_band,
            "total_stats": {
                "band_count": len(per_band),
                "overall_mean": float(np.mean(valid_means)) if valid_means else None,
                "total_pixels": total_pixels,
                "total_nodata": total_nodata,
                "overall_nodata_pct": round(
                    (total_nodata / total_pixels * 100.0), 4
                ) if total_pixels > 0 else 0.0,
            },
        }

    except Exception as exc:
        raise RasterStatisticsError(
            f"Failed to compute all statistics for '{path}': {exc}"
        ) from exc
