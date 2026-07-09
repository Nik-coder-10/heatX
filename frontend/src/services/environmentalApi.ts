export interface EnvironmentalData {
  annualPrecipitation: number;
  avgSummerTemp: number;
  avgWinterTemp: number;
  elevation: number;
}

const cache = new Map<string, { data: EnvironmentalData; ts: number }>();
const CACHE_TTL = 60 * 60 * 1000;

export async function fetchEnvironmentalData(lat: number, lng: number): Promise<EnvironmentalData> {
  const key = `${lat.toFixed(2)},${lng.toFixed(2)}`;
  const cached = cache.get(key);
  if (cached && Date.now() - cached.ts < CACHE_TTL) return cached.data;

  const [climateRes, elevRes] = await Promise.all([
    fetch(`https://climate-api.open-meteo.com/v1/climate?latitude=${lat.toFixed(2)}&longitude=${lng.toFixed(2)}&start_date=2020-01-01&end_date=2024-12-31&daily=precipitation_sum,temperature_2m_max,temperature_2m_min`, {
      signal: AbortSignal.timeout(15000),
    }),
    fetch(`https://api.open-meteo.com/v1/elevation?latitude=${lat.toFixed(2)}&longitude=${lng.toFixed(2)}`, {
      signal: AbortSignal.timeout(5000),
    }).catch(() => null),
  ]);

  if (!climateRes.ok) throw new Error(`Climate API: ${climateRes.status}`);

  const json = await climateRes.json();
  const precip = json.daily.precipitation_sum as (number | null)[];
  const tMax = json.daily.temperature_2m_max as (number | null)[];

  const validPrecip = precip.filter((p): p is number => p != null);
  const totalPrecip = validPrecip.reduce((a, b) => a + b, 0);
  const annualPrecipitation = totalPrecip / 5;

  const months = json.daily.time.map((t: string) => new Date(t).getUTCMonth());
  const isNorthern = lat >= 0;
  const summerMonths = isNorthern ? [4, 5, 6, 7, 8, 9] : [10, 11, 0, 1, 2, 3];
  const winterMonths = isNorthern ? [0, 1, 11] : [6, 7, 8];

  const summerTemps = tMax.filter((_, i) => tMax[i] != null && summerMonths.includes(months[i])) as number[];
  const winterTemps = tMax.filter((_, i) => tMax[i] != null && winterMonths.includes(months[i])) as number[];

  const avgSummerTemp = summerTemps.length > 0
    ? summerTemps.reduce((a, b) => a + b, 0) / summerTemps.length
    : 30;
  const avgWinterTemp = winterTemps.length > 0
    ? winterTemps.reduce((a, b) => a + b, 0) / winterTemps.length
    : 15;

  let elevation = 0;
  if (elevRes && elevRes.ok) {
    try {
      const elevJson = await elevRes.json();
      elevation = elevJson.elevation ?? 0;
    } catch {}
  }

  const data: EnvironmentalData = { annualPrecipitation, avgSummerTemp, avgWinterTemp, elevation };
  cache.set(key, { data, ts: Date.now() });
  return data;
}
