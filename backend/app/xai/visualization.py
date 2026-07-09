import logging
import os
from dataclasses import dataclass, field

import numpy as np

from .exceptions import VisualizationError

logger = logging.getLogger("app.xai.visualization")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    plt = None


def _check_matplotlib():
    if not HAS_MPL:
        raise VisualizationError("matplotlib is required for visualizations")


def render_shap_summary(
    shap_values: np.ndarray,
    X: np.ndarray,
    feature_names: list[str],
    output_path: str,
    max_features: int = 20,
    dpi: int = 150,
    format: str = "png",
) -> str:
    _check_matplotlib()
    if shap_values.ndim == 1:
        shap_values = shap_values.reshape(1, -1)

    fig, ax = plt.subplots(figsize=(10, max(4, min(max_features, len(feature_names)) * 0.4)))

    n_features = min(max_features, len(feature_names), shap_values.shape[1])
    importances = np.abs(shap_values).mean(axis=0)
    top_idx = np.argsort(importances)[-n_features:]

    values = []
    names = []
    for idx in top_idx:
        vals = shap_values[:, idx]
        values.append(vals)
        names.append(feature_names[idx] if idx < len(feature_names) else f"feat_{idx}")
    values = np.array(values)

    for i, (name, vals) in enumerate(zip(names, values)):
        pos = vals[vals > 0]
        neg = vals[vals <= 0]
        if len(pos) > 0:
            ax.scatter(pos, np.full_like(pos, i), alpha=0.4, s=8, c="#d9534f", edgecolors="none")
        if len(neg) > 0:
            ax.scatter(neg, np.full_like(neg, i), alpha=0.4, s=8, c="#5cb85c", edgecolors="none")

    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.set_xlabel("SHAP value (impact on prediction)")
    ax.set_ylabel("Feature")
    ax.axvline(0, color="gray", linestyle="--", linewidth=0.5)
    ax.set_title("SHAP Summary Plot")

    fig.tight_layout()
    fig.savefig(output_path, dpi=dpi, format=format, bbox_inches="tight")
    plt.close(fig)
    logger.info("SHAP summary saved to %s", output_path)
    return output_path


def render_shap_waterfall(
    shap_values: np.ndarray,
    feature_values: np.ndarray,
    feature_names: list[str],
    expected_value: float,
    prediction: float,
    output_path: str,
    max_features: int = 10,
    dpi: int = 150,
    format: str = "png",
) -> str:
    _check_matplotlib()

    if shap_values.ndim > 1:
        shap_values = shap_values.ravel()
    if feature_values.ndim > 1:
        feature_values = feature_values.ravel()

    n_features = min(max_features, len(feature_names))
    abs_shap = np.abs(shap_values)
    top_idx = np.argsort(abs_shap)[-n_features:][::-1]

    top_shap = shap_values[top_idx]
    top_names = [feature_names[i] for i in top_idx]
    top_vals = [feature_values[i] for i in top_idx]

    cumulative = np.zeros(n_features + 1)
    cumulative[0] = expected_value
    for i in range(n_features):
        cumulative[i + 1] = cumulative[i] + top_shap[i]

    fig, ax = plt.subplots(figsize=(10, 6))

    colors = ["#d9534f" if v >= 0 else "#5cb85c" for v in top_shap]
    bar_positions = np.arange(n_features)

    ax.barh(
        bar_positions,
        top_shap[::-1],
        left=cumulative[::-1][:n_features][::-1] - top_shap[::-1],
        color=colors[::-1],
        height=0.6,
    )

    for i, (name, val) in enumerate(zip(top_names, top_vals)):
        display_val = f"{val:.3f}" if abs(val) >= 0.001 else f"{val:.3e}"
        ax.text(
            cumulative[i] + top_shap[i] / 2,
            n_features - 1 - i,
            f"{name} = {display_val}",
            ha="center",
            va="center",
            fontsize=8,
            color="white" if abs(top_shap[i]) > abs(expected_value) * 0.3 else "black",
        )

    ax.set_yticks(bar_positions)
    ax.set_yticklabels([])
    ax.set_xlabel("Prediction")
    ax.set_title(f"SHAP Waterfall Plot (prediction = {prediction:.2f}, base = {expected_value:.2f})")
    ax.axvline(expected_value, color="gray", linestyle="--", linewidth=0.5)

    fig.tight_layout()
    fig.savefig(output_path, dpi=dpi, format=format, bbox_inches="tight")
    plt.close(fig)
    logger.info("SHAP waterfall saved to %s", output_path)
    return output_path


def render_feature_importance_bar(
    feature_names: list[str],
    importance_values: np.ndarray,
    output_path: str,
    title: str = "Feature Importance",
    max_features: int = 20,
    dpi: int = 150,
    format: str = "png",
    color: str = "#337ab7",
) -> str:
    _check_matplotlib()

    n_features = min(max_features, len(feature_names))
    idx = np.argsort(importance_values)[-n_features:]

    fig, ax = plt.subplots(figsize=(8, max(3, n_features * 0.35)))

    names = [feature_names[i] for i in idx]
    vals = importance_values[idx]

    ax.barh(range(len(names)), vals, color=color, height=0.6)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.set_xlabel("Importance (0-100)")
    ax.set_title(title)

    for i, v in enumerate(vals):
        ax.text(v + 0.5, i, f"{v:.1f}", va="center", fontsize=8)

    fig.tight_layout()
    fig.savefig(output_path, dpi=dpi, format=format, bbox_inches="tight")
    plt.close(fig)
    logger.info("Feature importance bar chart saved to %s", output_path)
    return output_path


def render_dependence_plot(
    shap_values: np.ndarray,
    X: np.ndarray,
    feature_names: list[str],
    feature_idx: int,
    output_path: str,
    dpi: int = 150,
    format: str = "png",
    interaction_feature: str | None = None,
) -> str:
    _check_matplotlib()

    fig, ax = plt.subplots(figsize=(8, 5))

    shap_vals = shap_values[:, feature_idx] if shap_values.ndim == 2 else shap_values
    feat_vals = X[:, feature_idx]

    if interaction_feature is not None and interaction_feature in feature_names:
        int_idx = feature_names.index(interaction_feature)
        int_vals = X[:, int_idx]
        scatter = ax.scatter(
            feat_vals, shap_vals, c=int_vals, cmap="coolwarm",
            alpha=0.6, s=20, edgecolors="none",
        )
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label(interaction_feature)
    else:
        ax.scatter(feat_vals, shap_vals, alpha=0.4, s=15, c="#337ab7", edgecolors="none")

    smooth_x = np.linspace(feat_vals.min(), feat_vals.max(), 100)
    try:
        from scipy.ndimage import uniform_filter1d
        sort_idx = np.argsort(feat_vals)
        sorted_shap = shap_vals[sort_idx]
        smoothed = uniform_filter1d(sorted_shap, size=max(3, len(sorted_shap) // 20))
        ax.plot(feat_vals[sort_idx], smoothed, color="red", linewidth=2, label="Trend")
    except Exception:
        pass

    ax.set_xlabel(feature_names[feature_idx])
    ax.set_ylabel("SHAP value")
    ax.set_title(f"SHAP Dependence Plot for {feature_names[feature_idx]}")
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=dpi, format=format, bbox_inches="tight")
    plt.close(fig)
    logger.info("Dependence plot saved to %s", output_path)
    return output_path


def render_interaction_heatmap(
    interaction_matrix: np.ndarray,
    feature_names: list[str],
    output_path: str,
    dpi: int = 150,
    format: str = "png",
    max_features: int = 15,
) -> str:
    _check_matplotlib()

    n_features = min(max_features, interaction_matrix.shape[0], len(feature_names))
    matrix = interaction_matrix[:n_features, :n_features]
    names = feature_names[:n_features]

    fig, ax = plt.subplots(figsize=(max(6, n_features * 0.5), max(5, n_features * 0.45)))

    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto", interpolation="nearest")

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Interaction Strength")

    ax.set_xticks(range(n_features))
    ax.set_yticks(range(n_features))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(names, fontsize=8)
    ax.set_title("Feature Interaction Matrix")

    fig.tight_layout()
    fig.savefig(output_path, dpi=dpi, format=format, bbox_inches="tight")
    plt.close(fig)
    logger.info("Interaction heatmap saved to %s", output_path)
    return output_path


def render_counterfactual_comparison(
    current_features: dict[str, float],
    suggested_changes: dict[str, dict],
    output_path: str,
    dpi: int = 150,
    format: str = "png",
) -> str:
    _check_matplotlib()

    if not suggested_changes:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No counterfactual changes suggested", ha="center", va="center", fontsize=12)
        fig.savefig(output_path, dpi=dpi, format=format, bbox_inches="tight")
        plt.close(fig)
        return output_path

    names = list(suggested_changes.keys())
    current_vals = [suggested_changes[n]["current"] for n in names]
    suggested_vals = [suggested_changes[n]["suggested"] for n in names]

    fig, ax = plt.subplots(figsize=(8, max(3, len(names) * 0.5)))

    y = np.arange(len(names))
    height = 0.35

    ax.barh(y - height / 2, current_vals, height, label="Current", color="#d9534f", alpha=0.7)
    ax.barh(y + height / 2, suggested_vals, height, label="Suggested", color="#5cb85c", alpha=0.7)

    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlabel("Feature Value")
    ax.set_title("Counterfactual Comparison")
    ax.legend()

    for i, (name, info) in enumerate(suggested_changes.items()):
        reduction = info.get("expected_temperature_reduction", 0)
        if reduction > 0:
            ax.text(
                max(current_vals[i], suggested_vals[i]) + 0.01,
                i,
                f"~{reduction:.2f}°C",
                va="center",
                fontsize=8,
                color="#333",
            )

    fig.tight_layout()
    fig.savefig(output_path, dpi=dpi, format=format, bbox_inches="tight")
    plt.close(fig)
    logger.info("Counterfactual comparison saved to %s", output_path)
    return output_path


def render_confidence_dashboard(
    confidence_metrics: dict,
    output_path: str,
    dpi: int = 150,
    format: str = "png",
) -> str:
    _check_matplotlib()

    labels = list(confidence_metrics.keys())
    values = list(confidence_metrics.values())

    fig, ax = plt.subplots(figsize=(8, 4))

    colors = ["#5cb85c" if v >= 0.7 else ("#f0ad4e" if v >= 0.4 else "#d9534f") for v in values]
    ax.bar(range(len(labels)), values, color=colors, width=0.5)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Score")
    ax.set_title("Confidence Dashboard")
    ax.axhline(0.7, color="green", linestyle="--", linewidth=0.5, label="Threshold (0.7)")
    ax.legend()

    for i, v in enumerate(values):
        ax.text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)

    fig.tight_layout()
    fig.savefig(output_path, dpi=dpi, format=format, bbox_inches="tight")
    plt.close(fig)
    logger.info("Confidence dashboard saved to %s", output_path)
    return output_path
