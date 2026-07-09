import logging
from datetime import datetime, timezone

import numpy as np

logger = logging.getLogger("app.features.temporal")

SEASONS_NH = {12: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2, 9: 3, 10: 3, 11: 3}


def extract_temporal_features(
    acquisition_date: str | datetime | None = None,
    baseline_year: int = 2020,
    compute_doy: bool = True,
    compute_month_feature: bool = True,
    compute_season_feature: bool = True,
    compute_time_feature: bool = True,
    compute_years_since: bool = True,
    acquisition_hour: float = 10.0,
) -> dict[str, np.ndarray]:
    result = {}

    if acquisition_date is None:
        return result

    if isinstance(acquisition_date, str):
        dt = datetime.fromisoformat(acquisition_date.replace("Z", "+00:00"))
    else:
        dt = acquisition_date

    year = dt.year
    doy = dt.timetuple().tm_yday
    month = dt.month

    season = SEASONS_NH.get(month, 0)
    years_since = year - baseline_year

    if compute_doy:
        result["day_of_year"] = np.array([doy], dtype=np.int32)
    if compute_month_feature:
        result["month"] = np.array([month], dtype=np.int32)
    if compute_season_feature:
        result["season"] = np.array([season], dtype=np.int32)
    if compute_time_feature:
        result["acquisition_time"] = np.array([acquisition_hour], dtype=np.float32)
    if compute_years_since:
        result["years_since_baseline"] = np.array([years_since], dtype=np.float32)

    return result
