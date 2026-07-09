import { fetchEnvironmentalData } from './environmentalApi';
import { fetchWeather } from './weatherApi';

export interface HeatspotData {
  temps: number[][];
  hotspots: { x: number; y: number; intensity: number }[];
  avgTemp: number;
  maxTemp: number;
  minTemp: number;
}

const ROWS = 40;
const COLS = 50;

function seededRandom(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) & 0x7fffffff;
    return s / 0x7fffffff;
  };
}

function gaussianRand(rng: () => number): number {
  const u = 1 - rng();
  const v = rng();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function normalize(v: number, min: number, max: number): number {
  if (max <= min) return 0.5;
  return Math.max(0, Math.min(1, (v - min) / (max - min)));
}

export async function predictHeatspots(
  lat: number,
  lng: number,
  currentTemp: number,
  annualPrecipitation: number,
  avgSummerTemp: number,
): Promise<HeatspotData> {
  const rng = seededRandom(Math.round(Math.abs(lat * 100 + lng * 100)));

  const precipMmYear = Math.max(100, annualPrecipitation);
  const precipRisk = 1 - normalize(precipMmYear, 100, 3000);

  const tempAnomaly = currentTemp - avgSummerTemp;
  const tempRisk = normalize(tempAnomaly + 10, 0, 20);

  const seasonalBoost = Math.abs(lat) < 23 ? 0.15 : 0;

  const temps: number[][] = [];
  const hotspots: { x: number; y: number; intensity: number }[] = [];

  const centerX = COLS / 2;
  const centerY = ROWS / 2;
  const maxDist = Math.hypot(centerX, centerY);

  const riskGrid: number[][] = [];

  for (let y = 0; y < ROWS; y++) {
    const row: number[] = [];
    const riskRow: number[] = [];
    for (let x = 0; x < COLS; x++) {
      const distFromCenter = Math.hypot(x - centerX, y - centerY) / maxDist;

      const urbanDensity = Math.exp(-distFromCenter * 2.5);
      const vegetation = 1 - urbanDensity * 0.7;

      const noise = gaussianRand(rng) * 0.12;
      const seasonalNoise = Math.sin(x * 0.4 + lat * 0.1) * Math.cos(y * 0.3 + lng * 0.1) * 0.08;

      const riskScore =
        urbanDensity * 0.30 +
        precipRisk * 0.25 +
        tempRisk * 0.20 +
        (1 - vegetation) * 0.15 +
        seasonalBoost * 0.10 +
        noise +
        seasonalNoise;

      riskRow.push(riskScore);

      const baseTemp = avgSummerTemp + tempAnomaly + riskScore * 8 - 3;
      const microClimate = gaussianRand(rng) * 1.0;
      const val = baseTemp + microClimate;
      row.push(Math.round(val * 100) / 100);
    }
    riskGrid.push(riskRow);
    temps.push(row);
  }

  const flatRisk = riskGrid.flat();
  const riskThreshold = flatRisk.sort((a, b) => b - a)[Math.min(15, flatRisk.length - 1)];

  const hotCells: { x: number; y: number; risk: number }[] = [];
  for (let y = 0; y < ROWS; y++) {
    for (let x = 0; x < COLS; x++) {
      if (riskGrid[y][x] >= riskThreshold) {
        hotCells.push({ x, y, risk: riskGrid[y][x] });
      }
    }
  }

  hotCells.sort((a, b) => b.risk - a.risk);
  const numHotspots = Math.min(hotCells.length, 8 + Math.floor(rng() * 7));
  const selected = hotCells.slice(0, numHotspots);

  for (const cell of selected) {
    const intensity = 0.55 + (cell.risk - riskThreshold) / (Math.max(...flatRisk) - riskThreshold) * 0.45;
    hotspots.push({ x: cell.x, y: cell.y, intensity: Math.round(intensity * 100) / 100 });
  }

  const flat = temps.flat();
  return {
    temps,
    hotspots,
    avgTemp: Math.round(flat.reduce((a, b) => a + b, 0) / flat.length * 100) / 100,
    maxTemp: Math.round(Math.max(...flat) * 100) / 100,
    minTemp: Math.round(Math.min(...flat) * 100) / 100,
  };
}

export async function getHeatspotData(lat: number, lng: number, currentTemp?: number): Promise<HeatspotData> {
  const [env, weather] = await Promise.all([
    fetchEnvironmentalData(lat, lng),
    currentTemp != null ? Promise.resolve({ currentTemp }) : fetchWeather(lat, lng).then(w => ({ currentTemp: w.currentTemp })),
  ]);

  const temp = currentTemp ?? weather.currentTemp;

  return predictHeatspots(lat, lng, temp, env.annualPrecipitation, env.avgSummerTemp);
}
