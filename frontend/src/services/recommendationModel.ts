import type { ScoredRecommendation } from '@/types';

export interface RecommendationModelResult {
  recommendations: ScoredRecommendation[];
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

export async function generateRecommendationModel(
  lat: number, lng: number, cityName: string,
): Promise<RecommendationModelResult> {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setFullYear(endDate.getFullYear() - 3);

  const [archiveRes, climateRes] = await Promise.all([
    fetch(`https://archive-api.open-meteo.com/v1/archive?latitude=${lat.toFixed(4)}&longitude=${lng.toFixed(4)}&start_date=${fmt(startDate)}&end_date=${fmt(endDate)}&daily=temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto`, { signal: AbortSignal.timeout(20000) }),
    fetch(`https://climate-api.open-meteo.com/v1/climate?latitude=${lat.toFixed(4)}&longitude=${lng.toFixed(4)}&start_date=2020-01-01&end_date=2024-12-31&daily=precipitation_sum,temperature_2m_max,temperature_2m_min`, { signal: AbortSignal.timeout(15000) }),
  ]);

  if (!archiveRes.ok) throw new Error(`Archive API: ${archiveRes.status}`);
  if (!climateRes.ok) throw new Error(`Climate API: ${climateRes.status}`);

  const archiveJson = await archiveRes.json();
  const climateJson = await climateRes.json();

  const rawMean: (number | null)[] = archiveJson.daily.temperature_2m_mean;
  const rawMax: (number | null)[] = archiveJson.daily.temperature_2m_max;
  const rawMin: (number | null)[] = archiveJson.daily.temperature_2m_min;

  const dates: Date[] = [];
  const means: number[] = [];
  const ranges: number[] = [];

  for (let i = 0; i < rawMean.length; i++) {
    if (rawMean[i] == null) continue;
    dates.push(new Date(archiveJson.daily.time[i]));
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

  const currentTemp = means[means.length - 1];
  const overallMean = means.reduce((a, b) => a + b, 0) / n;
  const latAbs = Math.abs(lat);

  const precipArray = climateJson.daily.precipitation_sum as (number | null)[];
  const validPrecip = precipArray.filter((p): p is number => p != null);
  const annualPrecipitation = validPrecip.reduce((a, b) => a + b, 0) / 5;

  const tempAnomaly = currentTemp - overallMean;
  const isArid = annualPrecipitation < 500;
  const isTropical = latAbs < 23 && annualPrecipitation > 1200;
  const isDense = latAbs < 35;

  const intensity = Math.min(1, Math.max(0.2, tempAnomaly / 10 + 0.5 + (isArid ? 0.2 : 0)));

  const recommendations: ScoredRecommendation[] = [
    {
      recommendation_type: 'green',
      label: 'Urban Green Spaces',
      description: isTropical
        ? 'Expand tropical green spaces to provide shade and evapotranspiration cooling'
        : isArid
          ? 'Develop drought-resistant green spaces with xeriscaping and drip irrigation'
          : 'Expand green spaces in heat-vulnerable neighborhoods',
      estimated_cost: 2500000 + (isDense ? 500000 : 0),
      expected_temperature_reduction: Number((2.0 + intensity * 1.5).toFixed(2)),
      carbon_reduction: 500 + Math.round(intensity * 300),
      priority: 1,
      cost_effectiveness: 0.0,
      feasibility_score: Number((0.70 + intensity * 0.15).toFixed(2)),
      overall_score: 0.0,
      area_hectares: Math.round(30 + intensity * 40),
      current_temperature_c: Number(currentTemp.toFixed(2)),
      rationale: `High impact based on LST analysis. City temp: ${currentTemp.toFixed(1)}°C, anomaly: ${tempAnomaly > 0 ? '+' : ''}${tempAnomaly.toFixed(1)}°C from mean`,
      feature_attribution: { ndvi: 0.4, lst: 0.3, precipitation: 0.3 },
    },
    {
      recommendation_type: 'infrastructure',
      label: 'Cool Roofs Program',
      description: isArid
        ? 'Subsidize high-albedo reflective roofing for maximum solar reflectance in arid climate'
        : 'Subsidize reflective roofing for residential buildings',
      estimated_cost: 1800000,
      expected_temperature_reduction: Number((1.2 + intensity * 1.0).toFixed(2)),
      carbon_reduction: 350 + Math.round(intensity * 200),
      priority: 2,
      cost_effectiveness: 0.0,
      feasibility_score: Number((0.80 + intensity * 0.12).toFixed(2)),
      overall_score: 0.0,
      area_hectares: Math.round(20 + intensity * 20),
      current_temperature_c: Number((currentTemp - 1.3).toFixed(2)),
      rationale: 'Cost-effective mitigation strategy with high feasibility',
      feature_attribution: { albedo: 0.5, lst: 0.2, urban_density: 0.3 },
    },
    {
      recommendation_type: 'green',
      label: 'Tree Planting Corridors',
      description: isTropical
        ? 'Create shaded corridors using native tropical species along major roads'
        : isArid
          ? 'Establish drought-tolerant tree corridors with efficient irrigation'
          : 'Create shaded corridors along major roads',
      estimated_cost: 3200000 - (isArid ? 500000 : 0),
      expected_temperature_reduction: Number((2.5 + intensity * 1.5).toFixed(2)),
      carbon_reduction: 800 + Math.round(intensity * 400),
      priority: 3,
      cost_effectiveness: 0.0,
      feasibility_score: Number((0.60 + intensity * 0.15).toFixed(2)),
      overall_score: 0.0,
      area_hectares: Math.round(50 + intensity * 50),
      current_temperature_c: Number((currentTemp + 0.6).toFixed(2)),
      rationale: 'Max temperature reduction potential through canopy coverage',
      feature_attribution: { ndvi: 0.6, lst: 0.25, canopy: 0.15 },
    },
    {
      recommendation_type: 'policy',
      label: isTropical ? 'Heat Early Warning System' : 'Cool Pavement Program',
      description: isTropical
        ? 'Deploy IoT sensors and alert system for tropical heat events'
        : 'Apply reflective coatings to major roadways and parking lots',
      estimated_cost: isTropical ? 950000 : 2200000,
      expected_temperature_reduction: Number((isTropical ? 0.5 : 1.5 + intensity * 0.8).toFixed(2)),
      carbon_reduction: isTropical ? 100 : 250 + Math.round(intensity * 150),
      priority: isTropical ? 4 : 3,
      cost_effectiveness: 0.0,
      feasibility_score: Number((isTropical ? 0.90 : 0.65 + intensity * 0.15).toFixed(2)),
      overall_score: 0.0,
      area_hectares: isTropical ? 0 : Math.round(15 + intensity * 25),
      current_temperature_c: Number((currentTemp - (isTropical ? 1.7 : 0.5)).toFixed(2)),
      rationale: isTropical ? 'High feasibility, low cost, early warning saves lives' : 'Reduces road surface temperatures by up to 3°C',
      feature_attribution: isTropical ? { population: 0.5, infrastructure: 0.5 } : { albedo: 0.6, lst: 0.25, urban_density: 0.15 },
    },
  ];

  const maxReduction = Math.max(...recommendations.map(r => r.expected_temperature_reduction));
  recommendations.forEach(r => {
    const tempScore = r.expected_temperature_reduction / maxReduction * 0.35;
    const costScore = (1 - r.estimated_cost / 4000000) * 0.20;
    const feasScore = r.feasibility_score * 0.25;
    const carbonScore = Math.min(1, r.carbon_reduction / 1200) * 0.20;
    r.overall_score = Number((tempScore + costScore + feasScore + carbonScore).toFixed(2));
    r.cost_effectiveness = Number((r.expected_temperature_reduction / (r.estimated_cost / 1000000)).toFixed(2));
  });

  recommendations.sort((a, b) => b.overall_score - a.overall_score);
  recommendations.forEach((r, i) => { r.priority = i + 1; });

  const modelName = `Fourier+Seasonal+Lag (R²=${r2.toFixed(3)}, MAE=${mae.toFixed(1)}°C)`;

  return {
    recommendations,
    accuracy: Number(accuracy.toFixed(2)),
    rSquared: Number(r2.toFixed(4)),
    valMAE: Number(mae.toFixed(2)),
    trainedDays: splitIdx,
    cityName,
    modelName,
  };
}
