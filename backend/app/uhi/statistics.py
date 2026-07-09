import logging
import numpy as np

logger = logging.getLogger("app.uhi.statistics")


def compute_uhi_statistics(hotspots: list, lst_celsius: np.ndarray | None = None) -> dict:
    if not hotspots:
        return {
            "n_hotspots": 0,
            "largest_uhi_sq_km": 0.0,
            "average_area_sq_km": 0.0,
            "average_lst_c": 0.0,
            "average_severity_score": 0.0,
            "severity_distribution": {},
            "area_distribution": {},
            "temperature_distribution": {},
        }

    areas = [h.area_sq_km for h in hotspots]
    temps = [h.mean_temperature_c for h in hotspots]
    sevs = [h.severity_score for h in hotspots]

    severity_dist = {}
    for h in hotspots:
        sev = h.severity
        severity_dist[sev] = severity_dist.get(sev, 0) + 1

    area_bins = [0, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0, float("inf")]
    area_labels = ["<0.1", "0.1-0.5", "0.5-1.0", "1.0-5.0", "5.0-10.0", "10.0-50.0", ">50"]
    area_dist = {}
    for label in area_labels:
        area_dist[label] = 0
    for a in areas:
        for i in range(len(area_bins) - 1):
            if area_bins[i] <= a < area_bins[i + 1]:
                area_dist[area_labels[i]] = area_dist.get(area_labels[i], 0) + 1
                break

    temp_bins = [0, 10, 20, 30, 35, 40, 45, 50, 60, float("inf")]
    temp_labels = ["<10", "10-20", "20-30", "30-35", "35-40", "40-45", "45-50", "50-60", ">60"]
    temp_dist = {}
    for label in temp_labels:
        temp_dist[label] = 0
    for t in temps:
        for i in range(len(temp_bins) - 1):
            if temp_bins[i] <= t < temp_bins[i + 1]:
                temp_dist[temp_labels[i]] = temp_dist.get(temp_labels[i], 0) + 1
                break

    return {
        "n_hotspots": len(hotspots),
        "largest_uhi_sq_km": float(max(areas)),
        "smallest_uhi_sq_km": float(min(areas)),
        "average_area_sq_km": float(np.mean(areas)),
        "total_area_sq_km": float(np.sum(areas)),
        "average_lst_c": float(np.mean(temps)),
        "max_lst_c": float(max(temps)),
        "min_lst_c": float(min(temps)),
        "average_severity_score": float(np.mean(sevs)),
        "max_severity_score": float(max(sevs)),
        "severity_distribution": severity_dist,
        "area_distribution_sq_km": area_dist,
        "temperature_distribution_c": temp_dist,
    }
