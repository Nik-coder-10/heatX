export interface ScenarioModelResult {
  simulations: SimulationOutput[];
  accuracy: number;
  rSquared: number;
  valMAE: number;
  trainedDays: number;
  cityName: string;
  modelName: string;
}

export interface SimulationOutput {
  scenario_name: string;
  mean_lst_baseline: number;
  mean_lst_simulated: number;
  mean_lst_change: number;
  max_lst_change: number;
  pct_improvement: number;
  total_area_ha: number;
  estimated_cost: number;
  estimated_co2_reduction: number;
  cost_effectiveness: number;
  parameters: Record<string, unknown>;
}

interface ScenarioDef {
  id: string;
  label: string;
  maxTempReduction: number;
  costPerHa: number;
  co2PerHa: number;
  areaFactor: number;
}

const SCENARIO_DEFS: ScenarioDef[] = [
  { id: 'trees', label: 'Tree Planting', maxTempReduction: 4.0, costPerHa: 2500000, co2PerHa: 1200, areaFactor: 0.8 },
  { id: 'roofs', label: 'Cool Roofs', maxTempReduction: 3.0, costPerHa: 1800000, co2PerHa: 600, areaFactor: 0.6 },
  { id: 'parks', label: 'Green Parks', maxTempReduction: 3.5, costPerHa: 3200000, co2PerHa: 900, areaFactor: 1.0 },
  { id: 'water', label: 'Water Features', maxTempReduction: 2.0, costPerHa: 4000000, co2PerHa: 300, areaFactor: 0.4 },
];

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

export async function runScenarioModel(
  lat: number,
  lng: number,
  cityName: string,
  scenarios: Array<{ id: string; intensity: number; active: boolean }>,
): Promise<ScenarioModelResult> {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setFullYear(endDate.getFullYear() - 3);

  const url = `https://archive-api.open-meteo.com/v1/archive?` +
    `latitude=${lat.toFixed(4)}&longitude=${lng.toFixed(4)}` +
    `&start_date=${fmt(startDate)}&end_date=${fmt(endDate)}` +
    `&daily=temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum` +
    `&timezone=auto`;

  const res = await fetch(url, { signal: AbortSignal.timeout(20000) });
  if (!res.ok) throw new Error(`Archive API: ${res.status}`);

  const json = await res.json();
  const rawMean: (number | null)[] = json.daily.temperature_2m_mean;
  const rawMax: (number | null)[] = json.daily.temperature_2m_max;
  const rawMin: (number | null)[] = json.daily.temperature_2m_min;
  const rawPrecip: (number | null)[] = json.daily.precipitation_sum;

  const dates: Date[] = [];
  const means: number[] = [];
  const ranges: number[] = [];
  const precip7d: number[] = [];

  for (let i = 0; i < rawMean.length; i++) {
    if (rawMean[i] == null) continue;
    dates.push(new Date(json.daily.time[i]));
    means.push(rawMean[i]!);
    const mx = rawMax[i] ?? rawMean[i]! + 2;
    const mn = rawMin[i] ?? rawMean[i]! - 2;
    ranges.push(mx - mn);
    let p7 = 0; for (let j = Math.max(0, i - 6); j <= i; j++) p7 += rawPrecip[j] ?? 0; precip7d.push(p7);
  }

  const n = means.length;
  if (n < 365) throw new Error(`Insufficient data for scenario model: ${n} days`);

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

  const seasonal: number[] = [];
  const sin1: number[] = []; const cos1: number[] = [];
  const sin2: number[] = []; const cos2: number[] = [];

  for (let i = 0; i < n; i++) {
    const key = `${dates[i].getMonth() + 1}-${dates[i].getDate()}`;
    seasonal.push(seasonalProfile.get(key) ?? 0);
    const theta = 2 * Math.PI * (dates[i].getTime() / 86400000 - new Date(dates[i].getFullYear(), 0, 0).getTime() / 86400000) / 365;
    sin1.push(Math.sin(theta)); cos1.push(Math.cos(theta));
    sin2.push(Math.sin(2 * theta)); cos2.push(Math.cos(2 * theta));
  }

  function buildRow(i: number): number[] {
    return [1.0, sin1[i], cos1[i], sin2[i], cos2[i], seasonal[i], ranges[i], precip7d[i]];
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

  const currentBaseline = means[means.length - 1];
  const currentSeasonalKey = `${new Date().getMonth() + 1}-${new Date().getDate()}`;
  const seasonalBaseline = seasonalProfile.get(currentSeasonalKey) ?? currentBaseline;

  const activeScenarios = scenarios.filter(s => s.active);
  const sims: SimulationOutput[] = activeScenarios.map(s => {
    const def = SCENARIO_DEFS.find(d => d.id === s.id)!;
    const reduction = def.maxTempReduction * s.intensity;
    const area = 50 + def.areaFactor * s.intensity * 120;
    const cost = def.costPerHa * area * (0.8 + 0.2 * s.intensity);
    const co2 = def.co2PerHa * area * s.intensity;
    const pctImprovement = (reduction / Math.max(1, currentBaseline - 5)) * 100;

    return {
      scenario_name: def.label,
      mean_lst_baseline: Number(currentBaseline.toFixed(2)),
      mean_lst_simulated: Number((currentBaseline - reduction).toFixed(2)),
      mean_lst_change: Number((-reduction).toFixed(2)),
      max_lst_change: Number((-reduction * 1.4).toFixed(2)),
      pct_improvement: Number(Math.min(100, Math.max(0, pctImprovement)).toFixed(2)),
      total_area_ha: Number(area.toFixed(2)),
      estimated_cost: Math.round(cost),
      estimated_co2_reduction: Number(co2.toFixed(2)),
      cost_effectiveness: Number(((reduction / Math.max(1, cost)) * 1000000).toFixed(4)),
      parameters: { intensity: s.intensity, scenarioId: s.id, seasonalBaseline: Number(seasonalBaseline.toFixed(2)) },
    };
  });

  const modelName = `Fourier+Seasonal+Lag (R²=${r2.toFixed(3)}, MAE=${mae.toFixed(1)}°C)`;

  return {
    simulations: sims,
    accuracy: Number(accuracy.toFixed(2)),
    rSquared: Number(r2.toFixed(4)),
    valMAE: Number(mae.toFixed(2)),
    trainedDays: splitIdx,
    cityName,
    modelName,
  };
}
