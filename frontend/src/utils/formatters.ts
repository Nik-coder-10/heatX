export function formatTemp(celsius: number): string {
  return `${celsius.toFixed(1)}°C`;
}

export function formatArea(km2: number): string {
  if (km2 >= 1) return `${km2.toFixed(2)} km²`;
  return `${(km2 * 100).toFixed(2)} ha`;
}

export function formatCurrency(usd: number): string {
  if (usd >= 1_000_000) return `$${(usd / 1_000_000).toFixed(2)}M`;
  if (usd >= 1_000) return `$${(usd / 1_000).toFixed(0)}K`;
  return `$${usd.toFixed(0)}`;
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function formatScore(value: number): string {
  return value.toFixed(2);
}

export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
    });
  } catch {
    return iso;
  }
}

export function formatCO2(tons: number): string {
  if (tons >= 1000) return `${(tons / 1000).toFixed(1)} kt CO₂e`;
  return `${tons.toFixed(0)} t CO₂e`;
}

export function roundTo(v: number, d: number = 2): number {
  return Math.round(v * 10 ** d) / 10 ** d;
}
