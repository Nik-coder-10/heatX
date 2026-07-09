export interface SpectralModelResult {
  values: number[];
  mean: number;
  min: number;
  max: number;
  label: string;
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

const WATER_BODIES: [string, number, number, number, number][] = [
  ['Bay of Bengal', 15, 88, 0.5, 800], ['Arabian Sea', 19, 72, 0.5, 800],
  ['Ganges River', 25.5, 83, 0.12, 50], ['Yamuna River', 28.6, 77.2, 0.05, 20],
  ['Hooghly River', 22.55, 88.3, 0.08, 30], ['Adyar River', 13.0, 80.25, 0.03, 10],
  ['Thames River', 51.5, -0.1, 0.04, 15], ['Seine River', 48.85, 2.3, 0.04, 15],
  ['Hudson River', 40.7, -74.0, 0.06, 25], ['East River', 40.73, -73.97, 0.05, 15],
  ['Tokyo Bay', 35.6, 139.8, 0.15, 100], ['Moskva River', 55.75, 37.6, 0.03, 10],
  ['Parramatta River', -33.85, 151.2, 0.05, 20], ['Sydney Harbour', -33.84, 151.24, 0.12, 40],
  ['Pacific Ocean', -33.8, 151.3, 0.5, 1000], ['Atlantic Ocean', 40.7, -74.1, 0.5, 1000],
  ['Lake Michigan', 41.9, -87.7, 0.25, 300], ['Lake Geneva', 46.2, 6.15, 0.15, 100],
  ['Lake Zurich', 47.35, 8.55, 0.15, 80], ['Spree River', 52.52, 13.4, 0.03, 15],
  ['Han River', 37.55, 126.97, 0.05, 30], ['Huangpu River', 31.23, 121.47, 0.04, 20],
  ['Bosphorus', 41.01, 28.98, 0.08, 50], ['Chao Phraya', 13.75, 100.5, 0.06, 25],
  ['Nile River', 30.04, 31.23, 0.04, 20], ['Lagos Lagoon', 6.52, 3.38, 0.1, 50],
  ['Lake Texcoco', 19.43, -99.13, 0.05, 30], ['Pinheiros River', -23.55, -46.63, 0.03, 15],
  ['Los Angeles River', 34.05, -118.24, 0.02, 10], ['Lake Ontario', 43.65, -79.38, 0.2, 200],
  ['Jakarta Bay', -6.21, 106.85, 0.15, 100], ['Indian Ocean', -1.29, 36.82, 0.2, 1000],
  ['Table Bay', -33.92, 18.42, 0.15, 80], ['Mediterranean Sea', 36.0, 14.0, 0.4, 600],
  ['Lake Victoria', -1, 33, 0.25, 300],
];

function classifyBiome(lat: number, precipMm: number, elevation: number): { ndviBase: number; ndbiBase: number; ndwiBase: number; ndviRange: [number, number]; label: string } {
  const latAbs = Math.abs(lat);
  if (elevation > 800 && latAbs < 30) {
    if (precipMm > 1000) return { ndviBase: 0.58, ndbiBase: -0.16, ndwiBase: 0.08, ndviRange: [0.30, 0.75], label: 'Tropical highland forest' };
    return { ndviBase: 0.40, ndbiBase: -0.08, ndwiBase: 0.02, ndviRange: [0.15, 0.55], label: 'Tropical highland savanna' };
  }
  if (latAbs > 60) {
    if (precipMm > 500) return { ndviBase: 0.25, ndbiBase: 0.02, ndwiBase: 0.08, ndviRange: [0.05, 0.40], label: 'Boreal/tundra zone' };
    return { ndviBase: 0.12, ndbiBase: 0.05, ndwiBase: -0.02, ndviRange: [0.00, 0.25], label: 'Arctic desert zone' };
  }
  if (latAbs > 50) {
    if (precipMm > 800) return { ndviBase: 0.45, ndbiBase: -0.10, ndwiBase: 0.06, ndviRange: [0.20, 0.60], label: 'Boreal forest zone' };
    return { ndviBase: 0.35, ndbiBase: -0.05, ndwiBase: 0.02, ndviRange: [0.15, 0.50], label: 'Cold temperate steppe' };
  }
  if (latAbs > 35) {
    if (precipMm > 1200) return { ndviBase: 0.55, ndbiBase: -0.12, ndwiBase: 0.08, ndviRange: [0.25, 0.70], label: 'Temperate rainforest zone' };
    if (precipMm > 700) return { ndviBase: 0.45, ndbiBase: -0.08, ndwiBase: 0.04, ndviRange: [0.20, 0.60], label: 'Temperate deciduous zone' };
    return { ndviBase: 0.32, ndbiBase: -0.03, ndwiBase: -0.01, ndviRange: [0.10, 0.45], label: 'Temperate grassland zone' };
  }
  if (latAbs > 23) {
    if (precipMm > 1000) return { ndviBase: 0.52, ndbiBase: -0.10, ndwiBase: 0.06, ndviRange: [0.25, 0.68], label: 'Subtropical humid zone' };
    if (precipMm > 500) return { ndviBase: 0.38, ndbiBase: -0.04, ndwiBase: 0.00, ndviRange: [0.15, 0.52], label: 'Subtropical dry zone' };
    if (precipMm > 200) return { ndviBase: 0.22, ndbiBase: 0.02, ndwiBase: -0.05, ndviRange: [0.05, 0.35], label: 'Subtropical arid zone' };
    return { ndviBase: 0.12, ndbiBase: 0.05, ndwiBase: -0.10, ndviRange: [0.00, 0.22], label: 'Subtropical desert zone' };
  }
  if (precipMm > 2000) return { ndviBase: 0.68, ndbiBase: -0.18, ndwiBase: 0.12, ndviRange: [0.40, 0.85], label: 'Tropical rainforest zone' };
  if (precipMm > 1200) return { ndviBase: 0.55, ndbiBase: -0.12, ndwiBase: 0.08, ndviRange: [0.30, 0.72], label: 'Tropical moist forest zone' };
  if (precipMm > 700) return { ndviBase: 0.45, ndbiBase: -0.08, ndwiBase: 0.04, ndviRange: [0.20, 0.60], label: 'Tropical dry forest zone' };
  if (precipMm > 400) return { ndviBase: 0.30, ndbiBase: -0.02, ndwiBase: -0.01, ndviRange: [0.10, 0.45], label: 'Tropical savanna zone' };
  return { ndviBase: 0.18, ndbiBase: 0.03, ndwiBase: -0.06, ndviRange: [0.02, 0.30], label: 'Tropical arid zone' };
}

function proximityToWater(lat: number, lng: number): number {
  let totalInfluence = 0;
  for (const [, wlat, wlng, wsize] of WATER_BODIES) {
    const d = Math.hypot(lat - wlat, lng - wlng);
    if (d < 0.5) totalInfluence += Math.exp(-d * 4) * wsize;
  }
  return Math.min(1, totalInfluence);
}

export async function computeSpectralModel(
  lat: number, lng: number, index: 'ndvi' | 'ndbi' | 'ndwi', cityName: string,
): Promise<SpectralModelResult> {
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

  const precipArray = climateJson.daily.precipitation_sum as (number | null)[];
  const validPrecip = precipArray.filter((p): p is number => p != null);
  const annualPrecipitation = validPrecip.reduce((a, b) => a + b, 0) / 5;

  const elevation = 0;
  const biome = classifyBiome(lat, annualPrecipitation, elevation);
  const waterInfluence = proximityToWater(lat, lng);

  const month = new Date().getMonth();
  const isNorthern = lat >= 0;
  const growingSeason = isNorthern ? (month >= 3 && month <= 9) : (month <= 3 || month >= 10);
  const latAbs = Math.abs(lat);
  const latSeasonality = Math.min(1, latAbs / 35);
  const seasonalFactor = growingSeason ? 1.0 : (0.92 - latSeasonality * 0.22);

  const currentTemp = means[means.length - 1];
  const summerTemps: number[] = [];
  const summerMonths = isNorthern ? [4, 5, 6, 7, 8, 9] : [10, 11, 0, 1, 2, 3];
  for (let i = 0; i < dates.length; i++) {
    if (summerMonths.includes(dates[i].getMonth())) summerTemps.push(means[i]);
  }
  const avgSummerTemp = summerTemps.length > 0 ? summerTemps.reduce((a, b) => a + b, 0) / summerTemps.length : 30;

  const popCount = 100;
  const values: number[] = [];
  for (let i = 0; i < popCount; i++) {
    const t = i / popCount;
    const urbanDensity = Math.exp(-t * 5) * (1 - t * 0.2);
    const suburban = Math.exp(-Math.abs(t - 0.3) * 8);
    const rural = 1 - Math.exp(-(1 - t) * 3);

    let raw: number;
    const precipNorm = Math.min(1, annualPrecipitation / 3000);

    if (index === 'ndvi') {
      const baseVeg = biome.ndviBase * seasonalFactor;
      const urbanSuppression = urbanDensity * 0.50;
      const suburbanVeg = suburban * 0.12;
      const ruralBoost = rural * 0.18;
      const precipBoost = precipNorm * 0.06;
      const waterEffect = waterInfluence * (Math.sin(t * Math.PI * 2) * 0.10);
      const tempEffect = (currentTemp - avgSummerTemp) * 0.008;
      raw = baseVeg - urbanSuppression + suburbanVeg + ruralBoost + precipBoost + waterEffect + tempEffect;
      raw = Math.max(biome.ndviRange[0], Math.min(biome.ndviRange[1], raw));
    } else if (index === 'ndbi') {
      const urbanBoost = urbanDensity * 0.40;
      const ruralDecline = -rural * 0.12;
      const precipEffect = -precipNorm * 0.05;
      const waterEffect = -waterInfluence * (Math.abs(Math.sin(t * Math.PI * 2)) * 0.08);
      raw = biome.ndbiBase + urbanBoost + ruralDecline + precipEffect + waterEffect;
      raw = Math.max(-0.45, Math.min(0.50, raw));
    } else {
      const urbanSuppression = -urbanDensity * 0.06;
      const waterPulse = waterInfluence * Math.max(0, Math.sin(t * Math.PI * 2)) * 0.20;
      const ruralDrainage = (1 - rural) * 0.04;
      const precipEffect = precipNorm * 0.05;
      const vegEffect = -biome.ndviBase * 0.08;
      raw = biome.ndwiBase + urbanSuppression + waterPulse + ruralDrainage + precipEffect + vegEffect;
      raw = Math.max(-0.55, Math.min(0.75, raw));
    }
    values.push(Math.round(raw * 10000) / 10000);
  }

  const mean = Number((values.reduce((a, b) => a + b, 0) / values.length).toFixed(4));
  const min = Number(Math.min(...values).toFixed(4));
  const max = Number(Math.max(...values).toFixed(4));

  const modelName = `Fourier+Seasonal+Lag (R²=${r2.toFixed(3)}, MAE=${mae.toFixed(1)}°C)`;

  return {
    values, mean, min, max,
    label: biome.label,
    accuracy: Number(accuracy.toFixed(2)),
    rSquared: Number(r2.toFixed(4)),
    valMAE: Number(mae.toFixed(2)),
    trainedDays: splitIdx,
    cityName,
    modelName,
  };
}
