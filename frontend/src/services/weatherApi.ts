export interface WeatherData {
  lat: number;
  lng: number;
  currentTemp: number;
  feelsLike: number;
  humidity: number;
  hourlyTemps: number[];
  time: string[];
}

const cache = new Map<string, { data: WeatherData; ts: number }>();
const CACHE_TTL = 10 * 60 * 1000;

export async function fetchWeather(lat: number, lng: number): Promise<WeatherData> {
  const key = `${lat.toFixed(2)},${lng.toFixed(2)}`;
  const cached = cache.get(key);
  if (cached && Date.now() - cached.ts < CACHE_TTL) {
    return cached.data;
  }

  const params = new URLSearchParams({
    latitude: lat.toFixed(2),
    longitude: lng.toFixed(2),
    current: 'temperature_2m,apparent_temperature,relative_humidity_2m',
    hourly: 'temperature_2m',
    forecast_days: '1',
    timezone: 'auto',
  });

  const res = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`, {
    signal: AbortSignal.timeout(8000),
  });

  if (!res.ok) throw new Error(`Weather API: ${res.status}`);

  const json = await res.json();

  const data: WeatherData = {
    lat: json.latitude,
    lng: json.longitude,
    currentTemp: json.current?.temperature_2m ?? 30,
    feelsLike: json.current?.apparent_temperature ?? json.current?.temperature_2m ?? 30,
    humidity: json.current?.relative_humidity_2m ?? 50,
    hourlyTemps: json.hourly?.temperature_2m ?? [],
    time: json.hourly?.time ?? [],
  };

  cache.set(key, { data, ts: Date.now() });
  return data;
}
