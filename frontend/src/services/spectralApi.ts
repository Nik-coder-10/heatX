import { fetchEnvironmentalData } from './environmentalApi';
import { fetchWeather } from './weatherApi';

export interface SpectralResult {
  values: number[];
  mean: number;
  min: number;
  max: number;
  label: string;
}

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

const WATER_BODIES: [string, number, number, number, number][] = [
  ['Bay of Bengal', 15, 88, 0.5, 800],
  ['Arabian Sea', 19, 72, 0.5, 800],
  ['Ganges River', 25.5, 83, 0.12, 50],
  ['Yamuna River', 28.6, 77.2, 0.05, 20],
  ['Hooghly River', 22.55, 88.3, 0.08, 30],
  ['Adyar River', 13.0, 80.25, 0.03, 10],
  ['Thames River', 51.5, -0.1, 0.04, 15],
  ['Seine River', 48.85, 2.3, 0.04, 15],
  ['Hudson River', 40.7, -74.0, 0.06, 25],
  ['East River', 40.73, -73.97, 0.05, 15],
  ['Tokyo Bay', 35.6, 139.8, 0.15, 100],
  ['Moskva River', 55.75, 37.6, 0.03, 10],
  ['Parramatta River', -33.85, 151.2, 0.05, 20],
  ['Sydney Harbour', -33.84, 151.24, 0.12, 40],
  ['Pacific Ocean', -33.8, 151.3, 0.5, 1000],
  ['Atlantic Ocean', 40.7, -74.1, 0.5, 1000],
  ['Lake Michigan', 41.9, -87.7, 0.25, 300],
  ['Lake Geneva', 46.2, 6.15, 0.15, 100],
  ['Lake Zurich', 47.35, 8.55, 0.15, 80],
  ['Spree River', 52.52, 13.4, 0.03, 15],
  ['Han River', 37.55, 126.97, 0.05, 30],
  ['Huangpu River', 31.23, 121.47, 0.04, 20],
  ['Bosphorus', 41.01, 28.98, 0.08, 50],
  ['Chao Phraya', 13.75, 100.5, 0.06, 25],
  ['Nile River', 30.04, 31.23, 0.04, 20],
  ['Lagos Lagoon', 6.52, 3.38, 0.1, 50],
  ['Lake Texcoco', 19.43, -99.13, 0.05, 30],
  ['Pinheiros River', -23.55, -46.63, 0.03, 15],
  ['Los Angeles River', 34.05, -118.24, 0.02, 10],
  ['Lake Ontario', 43.65, -79.38, 0.2, 200],
  ['Jakarta Bay', -6.21, 106.85, 0.15, 100],
  ['Arabian Sea', 24.86, 67.0, 0.3, 500],
  ['Indian Ocean', -1.29, 36.82, 0.2, 1000],
  ['Table Bay', -33.92, 18.42, 0.15, 80],
  ['Mediterranean Sea', 36.0, 14.0, 0.4, 600],
  ['Seine River', 48.85, 2.35, 0.04, 15],
  ['Lake Victoria', -1, 33, 0.25, 300],
];

interface BiomeParams {
  ndviBase: number;
  ndbiBase: number;
  ndwiBase: number;
  ndviRange: [number, number];
  label: string;
}

function classifyBiome(lat: number, lng: number, precipMm: number, elevation: number): BiomeParams {
  const latAbs = Math.abs(lat);
  const highElev = elevation > 800;

  // High-elevation (> 800m) override
  if (highElev && latAbs < 30) {
    if (precipMm > 1000) {
      return { ndviBase: 0.58, ndbiBase: -0.16, ndwiBase: 0.08, ndviRange: [0.30, 0.75], label: 'Tropical highland forest' };
    }
    return { ndviBase: 0.40, ndbiBase: -0.08, ndwiBase: 0.02, ndviRange: [0.15, 0.55], label: 'Tropical highland savanna' };
  }

  // True polar / tundra
  if (latAbs > 60) {
    if (precipMm > 500) {
      return { ndviBase: 0.25, ndbiBase: 0.02, ndwiBase: 0.08, ndviRange: [0.05, 0.40], label: 'Boreal/tundra zone' };
    }
    return { ndviBase: 0.12, ndbiBase: 0.05, ndwiBase: -0.02, ndviRange: [0.00, 0.25], label: 'Arctic desert zone' };
  }

  // Boreal / cold temperate
  if (latAbs > 50) {
    if (precipMm > 800) {
      return { ndviBase: 0.45, ndbiBase: -0.10, ndwiBase: 0.06, ndviRange: [0.20, 0.60], label: 'Boreal forest zone' };
    }
    return { ndviBase: 0.35, ndbiBase: -0.05, ndwiBase: 0.02, ndviRange: [0.15, 0.50], label: 'Cold temperate steppe' };
  }

  // Temperate (lat 35–50)
  if (latAbs > 35) {
    if (precipMm > 1200) {
      return { ndviBase: 0.55, ndbiBase: -0.12, ndwiBase: 0.08, ndviRange: [0.25, 0.70], label: 'Temperate rainforest zone' };
    }
    if (precipMm > 700) {
      return { ndviBase: 0.45, ndbiBase: -0.08, ndwiBase: 0.04, ndviRange: [0.20, 0.60], label: 'Temperate deciduous zone' };
    }
    return { ndviBase: 0.32, ndbiBase: -0.03, ndwiBase: -0.01, ndviRange: [0.10, 0.45], label: 'Temperate grassland zone' };
  }

  // Subtropical (lat 23–35)
  if (latAbs > 23) {
    if (precipMm > 1000) {
      return { ndviBase: 0.52, ndbiBase: -0.10, ndwiBase: 0.06, ndviRange: [0.25, 0.68], label: 'Subtropical humid zone' };
    }
    if (precipMm > 500) {
      return { ndviBase: 0.38, ndbiBase: -0.04, ndwiBase: 0.00, ndviRange: [0.15, 0.52], label: 'Subtropical dry zone' };
    }
    if (precipMm > 200) {
      return { ndviBase: 0.22, ndbiBase: 0.02, ndwiBase: -0.05, ndviRange: [0.05, 0.35], label: 'Subtropical arid zone' };
    }
    return { ndviBase: 0.12, ndbiBase: 0.05, ndwiBase: -0.10, ndviRange: [0.00, 0.22], label: 'Subtropical desert zone' };
  }

  // Tropical (lat < 23)
  if (precipMm > 2000) {
    return { ndviBase: 0.68, ndbiBase: -0.18, ndwiBase: 0.12, ndviRange: [0.40, 0.85], label: 'Tropical rainforest zone' };
  }
  if (precipMm > 1200) {
    return { ndviBase: 0.55, ndbiBase: -0.12, ndwiBase: 0.08, ndviRange: [0.30, 0.72], label: 'Tropical moist forest zone' };
  }
  if (precipMm > 700) {
    return { ndviBase: 0.45, ndbiBase: -0.08, ndwiBase: 0.04, ndviRange: [0.20, 0.60], label: 'Tropical dry forest zone' };
  }
  if (precipMm > 400) {
    return { ndviBase: 0.30, ndbiBase: -0.02, ndwiBase: -0.01, ndviRange: [0.10, 0.45], label: 'Tropical savanna zone' };
  }
  return { ndviBase: 0.18, ndbiBase: 0.03, ndwiBase: -0.06, ndviRange: [0.02, 0.30], label: 'Tropical arid zone' };
}

function proximityToWater(lat: number, lng: number): { waterInfluence: number; hasSignificantWater: boolean } {
  let totalInfluence = 0;
  for (const [, wlat, wlng, wsize] of WATER_BODIES) {
    const d = Math.hypot(lat - wlat, lng - wlng);
    if (d < 0.5) {
      totalInfluence += Math.exp(-d * 4) * wsize;
    }
  }
  return { waterInfluence: Math.min(1, totalInfluence), hasSignificantWater: totalInfluence > 0.08 };
}

function generateTransect(
  popCount: number,
  biome: BiomeParams,
  annualPrecipitation: number,
  elevation: number,
  waterInfluence: number,
  currentTemp: number,
  avgSummerTemp: number,
  seasonalFactor: number,
  lat: number,
  lng: number,
  index: 'ndvi' | 'ndbi' | 'ndwi',
): { values: number[]; mean: number; min: number; max: number } {
  const rng = seededRandom(Math.round(Math.abs(lat * 1000 + lng * 1000)));
  const precipNorm = Math.min(1, annualPrecipitation / 3000);
  const values: number[] = [];

  for (let i = 0; i < popCount; i++) {
    const t = i / popCount;

    // urban core at t=0, rural edge at t=1
    const urbanDensity = Math.exp(-t * 5) * (1 - t * 0.2);
    const suburban = Math.exp(-Math.abs(t - 0.3) * 8);
    const rural = 1 - Math.exp(-(1 - t) * 3);
    const noise = gaussianRand(rng) * 0.035;

    let raw: number;

    if (index === 'ndvi') {
      const baseVeg = biome.ndviBase * seasonalFactor;
      const urbanSuppression = urbanDensity * 0.50;
      const suburbanVeg = suburban * 0.12;
      const ruralBoost = rural * 0.18;
      const precipBoost = precipNorm * 0.06;
      const elevEffect = elevation > 500 ? 0.04 : 0;
      const waterEffect = waterInfluence * (Math.sin(t * Math.PI * 2) * 0.10);
      const tempEffect = -(currentTemp - avgSummerTemp) * 0.008;

      raw = baseVeg - urbanSuppression + suburbanVeg + ruralBoost + precipBoost + elevEffect + waterEffect + tempEffect + noise;
      raw = Math.max(biome.ndviRange[0], Math.min(biome.ndviRange[1], raw));

    } else if (index === 'ndbi') {
      const urbanBoost = urbanDensity * 0.40;
      const ruralDecline = -rural * 0.12;
      const precipEffect = -precipNorm * 0.05;
      const waterEffect = -waterInfluence * (Math.abs(Math.sin(t * Math.PI * 2)) * 0.08);

      raw = biome.ndbiBase + urbanBoost + ruralDecline + precipEffect + waterEffect + noise;
      raw = Math.max(-0.45, Math.min(0.50, raw));

    } else {
      const urbanSuppression = -urbanDensity * 0.06;
      const waterPulse = waterInfluence * Math.max(0, Math.sin(t * Math.PI * 2)) * 0.20;
      const ruralDrainage = (1 - rural) * 0.04;
      const precipEffect = precipNorm * 0.05;
      const vegEffect = -biome.ndviBase * 0.08;

      raw = biome.ndwiBase + urbanSuppression + waterPulse + ruralDrainage + precipEffect + vegEffect + noise;
      raw = Math.max(-0.55, Math.min(0.75, raw));
    }

    values.push(Math.round(raw * 10000) / 10000);
  }

  return {
    values,
    mean: Math.round(values.reduce((a, b) => a + b, 0) / values.length * 10000) / 10000,
    min: Math.round(Math.min(...values) * 10000) / 10000,
    max: Math.round(Math.max(...values) * 10000) / 10000,
  };
}

export async function computeSpectralIndex(
  lat: number, lng: number, index: 'ndvi' | 'ndbi' | 'ndwi',
): Promise<SpectralResult> {
  const [env, weather] = await Promise.all([
    fetchEnvironmentalData(lat, lng),
    fetchWeather(lat, lng).catch(() => null),
  ]);

  const currentTemp = weather?.currentTemp ?? env.avgSummerTemp;
  const biome = classifyBiome(lat, lng, env.annualPrecipitation, env.elevation);
  const water = proximityToWater(lat, lng);

  const month = new Date().getMonth();
  const isNorthern = lat >= 0;
  const growingSeason = isNorthern ? (month >= 3 && month <= 9) : (month <= 3 || month >= 10);
  const latAbs = Math.abs(lat);
  const latSeasonality = Math.min(1, latAbs / 35);
  const seasonalFactor = growingSeason ? 1.0 : (0.92 - latSeasonality * 0.22);

  const result = generateTransect(
    100, biome, env.annualPrecipitation, env.elevation, water.waterInfluence,
    currentTemp, env.avgSummerTemp, seasonalFactor, lat, lng, index,
  );

  return { ...result, label: biome.label };
}
