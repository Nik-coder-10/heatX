import logging
import numpy as np

from .severity import SEVERITY_COLORS

logger = logging.getLogger("app.uhi.visualization")


def render_hotspot_map(
    lst_celsius: np.ndarray,
    hotspots: list,
    output_path: str,
    severity_map: np.ndarray | None = None,
    title: str = "Urban Heat Island Detection",
) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    from matplotlib.colors import LinearSegmentedColormap

    fig, ax = plt.subplots(figsize=(12, 10))

    cmap = LinearSegmentedColormap.from_list(
        "thermal", ["blue", "cyan", "green", "yellow", "red"], N=256
    )
    im = ax.imshow(lst_celsius, cmap=cmap, alpha=0.7)
    plt.colorbar(im, ax=ax, label="Temperature (C)", shrink=0.7)

    severity_order = ["Very Low", "Low", "Moderate", "High", "Very High", "Extreme"]
    color_map = {s: SEVERITY_COLORS.get(s, "#ffffff") for s in severity_order}

    for hs in hotspots:
        geom = hs.geometry
        if geom.get("type") == "Polygon":
            coords = np.array(geom["coordinates"][0])
            if coords.shape[1] == 2:
                poly = Polygon(coords, closed=True,
                               facecolor=color_map.get(hs.severity, "red"),
                               edgecolor="black", linewidth=0.5, alpha=0.4)
                ax.add_patch(poly)

    ax.set_title(title)
    ax.axis("off")

    legend_elements = []
    for sev in severity_order:
        if sev in color_map:
            from matplotlib.patches import Patch
            legend_elements.append(
                Patch(facecolor=color_map[sev], alpha=0.6, label=sev)
            )
    if legend_elements:
        ax.legend(handles=legend_elements, loc="lower right", fontsize=8)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Hotspot map saved to %s", output_path)
    return output_path


def render_severity_heatmap(
    severity_map: np.ndarray,
    output_path: str,
    title: str = "UHI Severity Classification",
) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    sev_colors = ["#2c7bb6", "#abd9e9", "#ffffbf", "#fdae61", "#f46d43", "#d7191c"]
    cmap = LinearSegmentedColormap.from_list("severity", sev_colors, N=6)

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(severity_map, cmap=cmap, vmin=0, vmax=5)
    cbar = fig.colorbar(im, ax=ax, ticks=[0, 1, 2, 3, 4, 5], shrink=0.7)
    cbar.ax.set_yticklabels(["Very Low", "Low", "Moderate", "High", "Very High", "Extreme"])
    ax.set_title(title)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Severity heatmap saved to %s", output_path)
    return output_path


def render_boundary_overlay(
    lst_celsius: np.ndarray,
    binary_mask: np.ndarray,
    output_path: str,
    title: str = "UHI Boundary Overlay",
) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(lst_celsius, cmap="gray", alpha=0.6)
    from scipy.ndimage import binary_dilation, binary_erosion
    boundary = binary_dilation(binary_mask) & ~binary_erosion(binary_mask)
    overlay = np.zeros((*lst_celsius.shape, 4), dtype=np.float32)
    overlay[boundary, 0] = 1.0
    overlay[boundary, 3] = 0.8
    ax.imshow(overlay)
    ax.set_title(title)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path
