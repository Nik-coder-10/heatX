import logging
import numpy as np

logger = logging.getLogger("app.lst.visualization")


def _thermal_colormap():
    try:
        import matplotlib.pyplot as plt
        from matplotlib.colors import LinearSegmentedColormap
    except ImportError:
        return None

    colors = [
        (0.0, 0.0, 0.3),
        (0.0, 0.0, 1.0),
        (0.0, 0.5, 1.0),
        (0.0, 1.0, 0.5),
        (0.5, 1.0, 0.0),
        (1.0, 1.0, 0.0),
        (1.0, 0.5, 0.0),
        (1.0, 0.0, 0.0),
        (0.5, 0.0, 0.0),
    ]
    return LinearSegmentedColormap.from_list("thermal", colors, N=256)


def render_temperature_map(
    lst: np.ndarray,
    output_path: str,
    lst_min: float | None = None,
    lst_max: float | None = None,
    title: str = "Land Surface Temperature",
) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = lst.astype(np.float64)
    valid = np.isfinite(data)
    if not valid.any():
        logger.warning("No valid data to render")
        return ""

    vmin = lst_min if lst_min is not None else float(np.nanmin(data))
    vmax = lst_max if lst_max is not None else float(np.nanmax(data))
    if vmin == vmax:
        vmax = vmin + 1.0

    cmap = _thermal_colormap()
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax)
    cbar = fig.colorbar(im, ax=ax, label="Temperature (°C)", shrink=0.75)
    ax.set_title(title)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Temperature map saved to %s", output_path)
    return output_path


def render_histogram(
    lst: np.ndarray,
    output_path: str,
    title: str = "LST Distribution",
) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = lst.astype(np.float64)
    valid = data[np.isfinite(data)]
    if valid.size == 0:
        logger.warning("No valid data for histogram")
        return ""

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(valid, bins=50, color="coral", edgecolor="black", alpha=0.7)
    ax.set_xlabel("Temperature (°C)")
    ax.set_ylabel("Pixel Count")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Histogram saved to %s", output_path)
    return output_path


def render_hotspot_overlay(
    lst: np.ndarray,
    output_path: str,
    threshold_percentile: float = 90.0,
) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    data = lst.astype(np.float64)
    valid = data[np.isfinite(data)]
    if valid.size == 0:
        logger.warning("No valid data for hotspot overlay")
        return ""

    threshold = float(np.percentile(valid, threshold_percentile))
    hotspot_mask = data > threshold

    cmap = _thermal_colormap()
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(data, cmap=cmap, alpha=0.6)
    ax.imshow(hotspot_mask.astype(float), cmap="Reds", alpha=0.4)
    ax.set_title(f"Urban Hotspot Overlay (>p{int(threshold_percentile)}: {threshold:.1f}°C)")
    ax.axis("off")

    legend_elements = [
        Rectangle((0, 0), 1, 1, facecolor="red", alpha=0.4, label=f"Hotspot >{threshold:.1f}°C"),
    ]
    ax.legend(handles=legend_elements, loc="lower right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Hotspot overlay saved to %s", output_path)
    return output_path
