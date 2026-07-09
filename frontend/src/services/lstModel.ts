export interface LSTModelResult {
  current: number;
  mean: number;
  max: number;
  min: number;
  values: number[];
  predicted: number[];
  date_range: { start: string; end: string };
  accuracy: number;
  rSquared: number;
  valMAE: number;
  trainedDays: number;
  cityName: string;
  modelName: string;
}

function fmt(d: Date): string {
  return d.toISOString().split('T')[0];
}

function smoothArray(arr: number[], window: number): number[] {
  const result: number[] = [];
  for (let i = 0; i < arr.length; i++) {
    let sum = 0; let count = 0;
    const half = Math.floor(window / 2);
    for (let w = -half; w <= half; w++) {
      const idx = ((i + w) % arr.length + arr.length) % arr.length;
      if (isFinite(arr[idx])) { sum += arr[idx]; count++; }
    }
    result.push(count > 0 ? sum / count : arr[i]);
  }
  return result;
}

function computeR2(actuals: number[], predictions: number[]): number {
  const n = Math.min(actuals.length, predictions.length);
  if (n < 3) return 0;
  const mean = actuals.reduce((a, b) => a + b, 0) / n;
  let ssRes = 0, ssTot = 0;
  for (let i = 0; i < n; i++) {
    if (!isFinite(actuals[i]) || !isFinite(predictions[i])) continue;
    ssRes += (actuals[i] - predictions[i]) ** 2;
    ssTot += (actuals[i] - mean) ** 2;
  }
  return ssTot > 0 ? Math.max(0, Math.min(1, 1 - ssRes / ssTot)) : 0;
}

function computeMAE(actuals: number[], predictions: number[]): number {
  let sum = 0; let count = 0;
  for (let i = 0; i < Math.min(actuals.length, predictions.length); i++) {
    if (isFinite(actuals[i]) && isFinite(predictions[i])) {
      sum += Math.abs(actuals[i] - predictions[i]); count++;
    }
  }
  return count > 0 ? sum / count : 999;
}

function solveOLS(designMatrix: number[][], targets: number[]): number[] {
  const n = designMatrix.length;
  const m = designMatrix[0].length;
  const XtX: number[][] = Array.from({ length: m }, () => new Array(m).fill(0));
  const Xty: number[] = new Array(m).fill(0);
  for (let i = 0; i < n; i++) {
    for (let r = 0; r < m; r++) {
      for (let c = 0; c < m; c++) XtX[r][c] += designMatrix[i][r] * designMatrix[i][c];
      Xty[r] += designMatrix[i][r] * targets[i];
    }
  }
  const aug: number[][] = XtX.map((row, r) => [...row, Xty[r]]);
  for (let col = 0; col < m; col++) {
    let maxVal = Math.abs(aug[col][col]), maxRow = col;
    for (let r = col + 1; r < m; r++) {
      if (Math.abs(aug[r][col]) > maxVal) { maxVal = Math.abs(aug[r][col]); maxRow = r; }
    }
    if (maxRow !== col) [aug[col], aug[maxRow]] = [aug[maxRow], aug[col]];
    if (Math.abs(aug[col][col]) < 1e-12) continue;
    for (let r = col + 1; r < m; r++) {
      const factor = aug[r][col] / aug[col][col];
      for (let c = col; c <= m; c++) aug[r][c] -= factor * aug[col][c];
    }
  }
  const beta = new Array(m).fill(0);
  for (let r = m - 1; r >= 0; r--) {
    let sum = aug[r][m];
    for (let c = r + 1; c < m; c++) sum -= aug[r][c] * beta[c];
    beta[r] = Math.abs(aug[r][r]) > 1e-12 ? sum / aug[r][r] : 0;
  }
  return beta;
}

export async function computeLSTModel(
  lat: number, lng: number, cityName: string, days: number = 30,
): Promise<LSTModelResult> {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setFullYear(endDate.getFullYear() - 3);

  const url = `https://archive-api.open-meteo.com/v1/archive?latitude=${lat.toFixed(4)}&longitude=${lng.toFixed(4)}&start_date=${fmt(startDate)}&end_date=${fmt(endDate)}&daily=temperature_2m_mean,temperature_2m_max,temperature_2m_min&timezone=auto`;

  const res = await fetch(url, { signal: AbortSignal.timeout(20000) });
  if (!res.ok) throw new Error(`Archive API: ${res.status}`);

  const json = await res.json();
  const rawMean: (number | null)[] = json.daily.temperature_2m_mean;
  const rawMax: (number | null)[] = json.daily.temperature_2m_max;
  const rawMin: (number | null)[] = json.daily.temperature_2m_min;

  const dates: Date[] = [];
  const means: number[] = [];
  const ranges: number[] = [];

  for (let i = 0; i < rawMean.length; i++) {
    if (rawMean[i] == null) continue;
    dates.push(new Date(json.daily.time[i]));
    means.push(rawMean[i]!);
    const mx = rawMax[i] ?? rawMean[i]! + 2;
    const mn = rawMin[i] ?? rawMean[i]! - 2;
    ranges.push(mx - mn);
  }

  const n = means.length;
  if (n < 365) throw new Error(`Insufficient data: ${n} days`);

  const profileMap = new Map<string, number[]>();
  for (let i = 0; i < n; i++) {
    const key = `${dates[i].getMonth() + 1}-${dates[i].getDate()}`;
    if (!profileMap.has(key)) profileMap.set(key, []);
    profileMap.get(key)!.push(means[i]);
  }
  const sortedKeys = Array.from(profileMap.keys()).sort((a, b) => {
    const [ma, da] = a.split('-').map(Number);
    const [mb, db] = b.split('-').map(Number);
    return ma !== mb ? ma - mb : da - db;
  });
  let rawProfile = sortedKeys.map(k => {
    const vals = profileMap.get(k)!;
    return vals.reduce((a, b) => a + b, 0) / vals.length;
  });
  for (let iter = 0; iter < 5; iter++) rawProfile = smoothArray(rawProfile, 15);
  const seasonalProfile = new Map<string, number>();
  sortedKeys.forEach((k, i) => seasonalProfile.set(k, rawProfile[i]));

  const sin1: number[] = []; const cos1: number[] = [];
  const sin2: number[] = []; const cos2: number[] = [];
  const seasonal: number[] = [];
  const lag1: number[] = new Array(n).fill(0);

  for (let i = 0; i < n; i++) {
    const key = `${dates[i].getMonth() + 1}-${dates[i].getDate()}`;
    seasonal.push(seasonalProfile.get(key) ?? 0);
    const theta = 2 * Math.PI * (dates[i].getTime() / 86400000 - new Date(dates[i].getFullYear(), 0, 0).getTime() / 86400000) / 365;
    sin1.push(Math.sin(theta)); cos1.push(Math.cos(theta));
    sin2.push(Math.sin(2 * theta)); cos2.push(Math.cos(2 * theta));
    if (i > 0) lag1[i] = means[i - 1];
  }

  function buildRow(i: number): number[] {
    return [1.0, sin1[i], cos1[i], sin2[i], cos2[i], seasonal[i], ranges[i], lag1[i]];
  }

  const splitIdx = Math.floor(n * 0.8);
  const dm: number[][] = [];
  for (let i = 3; i < splitIdx; i++) dm.push(buildRow(i));
  const targets = means.slice(3, splitIdx);
  const coeffs = solveOLS(dm, targets);

  const valPreds: number[] = [];
  for (let i = splitIdx; i < n; i++) {
    const row = buildRow(i);
    valPreds.push(row.reduce((sum, v, j) => sum + v * coeffs[j], 0));
  }
  const valActuals = means.slice(splitIdx);
  const r2 = computeR2(valActuals, valPreds);
  const mae = computeMAE(valActuals, valPreds);
  const accuracy = Math.max(0, Math.min(100, r2 * 100));

  const trainingEnd = new Date(endDate);
  trainingEnd.setDate(trainingEnd.getDate() - (n - splitIdx));

  const values = means.slice(-days);
  const current = values[values.length - 1];
  const mean = Number((values.reduce((a, b) => a + b, 0) / values.length).toFixed(2));
  const max = Number(Math.max(...values).toFixed(2));
  const min = Number(Math.min(...values).toFixed(2));

  const forecastDays = 7;
  const predicted: number[] = [];
  const recentRanges = ranges.slice(-90);
  const avgRange = recentRanges.reduce((a, b) => a + b, 0) / recentRanges.length;

  for (let i = 0; i < forecastDays; i++) {
    const futureDate = new Date(endDate);
    futureDate.setDate(futureDate.getDate() + i + 1);
    const key = `${futureDate.getMonth() + 1}-${futureDate.getDate()}`;
    const theta = 2 * Math.PI * (futureDate.getTime() / 86400000 - new Date(futureDate.getFullYear(), 0, 0).getTime() / 86400000) / 365;
    const row: number[] = [1.0];
    row.push(Math.sin(theta)); row.push(Math.cos(theta));
    row.push(Math.sin(2 * theta)); row.push(Math.cos(2 * theta));
    row.push(seasonalProfile.get(key) ?? 0);
    row.push(avgRange);
    row.push(current);
    predicted.push(Number(row.reduce((sum, v, j) => sum + v * coeffs[j], 0).toFixed(2)));
  }

  const modelName = `Fourier+Seasonal+Lag (R²=${r2.toFixed(3)}, MAE=${mae.toFixed(1)}°C)`;

  return {
    current, mean, max, min,
    values,
    predicted,
    date_range: { start: fmt(new Date(endDate.getTime() - days * 86400000)), end: fmt(endDate) },
    accuracy: Number(accuracy.toFixed(2)),
    rSquared: Number(r2.toFixed(4)),
    valMAE: Number(mae.toFixed(2)),
    trainedDays: splitIdx,
    cityName,
    modelName,
  };
}
