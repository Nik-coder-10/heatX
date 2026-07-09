const SEVERITY_COLORS: Record<string, string> = {
  very_low: '#22c55e',
  low: '#86efac',
  moderate: '#fbbf24',
  high: '#f97316',
  very_high: '#ef4444',
  extreme: '#dc2626',
};

const LANDCOVER_COLORS: Record<string, string> = {
  builtup: '#ef4444',
  vegetation: '#22c55e',
  water: '#3b82f6',
  barren: '#a16207',
  agriculture: '#fbbf24',
  forest: '#16a34a',
  wetland: '#06b6d4',
};

const INDEX_COLORS = {
  ndvi: ['#2563eb', '#22c55e', '#16a34a'],
  ndbi: ['#fef9c3', '#f97316', '#dc2626'],
  lst: ['#1e3a5f', '#f97316', '#dc2626', '#7f1d1d'],
  ndwi: ['#92400e', '#3b82f6', '#1e40af'],
};

export function getSeverityColor(severity: string): string {
  return SEVERITY_COLORS[severity.toLowerCase()] || '#6b7280';
}

export function getLandcoverColor(landcover: string): string {
  return LANDCOVER_COLORS[landcover.toLowerCase()] || '#6b7280';
}

export function getIndexColorScheme(index: string): string[] {
  return INDEX_COLORS[index.toLowerCase() as keyof typeof INDEX_COLORS] || ['#6366f1', '#818cf8', '#a5b4fc'];
}

export function severityToOpacity(severity: string): number {
  const map: Record<string, number> = {
    very_low: 0.3, low: 0.4, moderate: 0.5, high: 0.6, very_high: 0.7, extreme: 0.8,
  };
  return map[severity.toLowerCase()] || 0.4;
}
