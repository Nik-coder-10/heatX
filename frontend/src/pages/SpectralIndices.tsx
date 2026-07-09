import { useState, useEffect, useRef } from 'react';
import { Card, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { CanvasHeatmap } from '@/components/map/CanvasHeatmap';
import { HistogramChart } from '@/components/charts/HistogramChart';
import { useLocationParams } from '@/hooks/useLocationParams';
import { computeSpectralModel, type SpectralModelResult } from '@/services/spectralModel';
import { BarChart3, Check, RefreshCw, Brain, CheckCircle2, XCircle } from 'lucide-react';
import { LOCATIONS } from '@/services/locations';
import { clsx } from 'clsx';
import { Badge } from '@/components/ui/Badge';

const indexOptions = [
  { value: 'ndvi' as const, label: 'NDVI — Normalized Difference Vegetation Index' },
  { value: 'ndbi' as const, label: 'NDBI — Normalized Difference Built-up Index' },
  { value: 'ndwi' as const, label: 'NDWI — Normalized Difference Water Index' },
];

const cache = new Map<string, SpectralModelResult>();

export default function SpectralIndices() {
  const loc = useLocationParams();
  const [selected, setSelected] = useState<'ndvi' | 'ndbi' | 'ndwi'>('ndvi');
  const [computing, setComputing] = useState(false);
  const [result, setResult] = useState<SpectralModelResult | null>(null);
  const mounted = useRef(true);

  const [cityIdx, setCityIdx] = useState(() => {
    const idx = LOCATIONS.findIndex(c => Math.abs(c.lat - loc.lat) < 0.5 && Math.abs(c.lng - loc.lng) < 0.5);
    return idx >= 0 ? idx : 1;
  });

  const city = LOCATIONS[cityIdx];

  const cacheKey = `${city.lat.toFixed(3)},${city.lng.toFixed(3)}:${selected}`;

  const compute = async (force = false) => {
    const cached = cache.get(cacheKey);
    if (cached && !force) { setResult(cached); return; }

    setComputing(true);
    try {
      const data = await computeSpectralModel(city.lat, city.lng, selected, city.name);
      if (!mounted.current) return;
      cache.set(cacheKey, data);
      setResult(data);
    } catch (e) {
      console.warn('Spectral compute failed:', e);
    } finally {
      if (mounted.current) setComputing(false);
    }
  };

  useEffect(() => { compute(); }, [cacheKey]);
  useEffect(() => { return () => { mounted.current = false; }; }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-lg font-semibold text-text-primary">Spectral Indices</h1>
            <p className="text-sm text-text-secondary mt-0.5">
              {city.name ? `${city.name} — ` : ''}NDVI / NDBI / NDWI with ML-validated model
            </p>
          </div>
          {result && (
            <span className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-medium bg-accent/10 text-accent border border-accent/20">
              <span className="w-1.5 h-1.5 rounded-full bg-accent/60" />
              {result.label}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => compute(true)} loading={computing} variant="secondary" size="sm">
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </Button>
          <Button onClick={() => compute(false)} loading={computing}>
            <BarChart3 className="h-3.5 w-3.5" /> Compute Index
          </Button>
        </div>
      </div>

      {result && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="stat-card">
            <div className="flex items-center gap-2 mb-1">
              <Brain className="h-3.5 w-3.5 text-accent" />
              <span className="text-xs text-text-secondary uppercase tracking-wider">Model</span>
            </div>
            <p className="text-sm font-bold text-text-primary truncate">{result.modelName}</p>
          </div>
          <div className="stat-card">
            <p className="text-2xs text-text-secondary uppercase tracking-wider mb-1">R² Score</p>
            <p className="text-lg font-bold text-text-primary">{result.rSquared.toFixed(3)}</p>
          </div>
          <div className="stat-card">
            <p className="text-2xs text-text-secondary uppercase tracking-wider mb-1">Accuracy</p>
            <p className="text-lg font-bold text-text-primary">{result.accuracy.toFixed(1)}%</p>
            <div className="flex items-center gap-1 text-2xs">
              {result.accuracy >= 95 ? (
                <><CheckCircle2 className="h-3 w-3 text-success" /> 95%+ target met</>
              ) : (
                <><XCircle className="h-3 w-3 text-warning" /> below 95%</>
              )}
            </div>
          </div>
          <div className="stat-card">
            <p className="text-2xs text-text-secondary uppercase tracking-wider mb-1">Val MAE</p>
            <p className="text-lg font-bold text-text-primary">{result.valMAE}°C</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <Card padding="lg">
            <CardTitle className="mb-3">Index Selection</CardTitle>
            <div className="space-y-1.5">
              {indexOptions.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setSelected(opt.value)}
                  className={clsx(
                    'w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all duration-200',
                    selected === opt.value
                      ? 'bg-accent/10 text-accent border border-accent/20'
                      : 'text-text-secondary hover:bg-white/5 hover:text-text-primary border border-transparent',
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span>{opt.label}</span>
                    {selected === opt.value && <Check className="h-3.5 w-3.5" />}
                  </div>
                </button>
              ))}
            </div>
          </Card>

          <Card padding="lg">
            <CardTitle className="mb-3">City</CardTitle>
            <Select label="Location" value={String(cityIdx)} onChange={(e) => setCityIdx(Number(e.target.value))} options={LOCATIONS.map((c, i) => ({ value: String(i), label: c.name }))} />
          </Card>

          {result && (
            <Card padding="lg">
              <CardTitle className="mb-3">Summary</CardTitle>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-text-secondary">Mean</span>
                  <span className="text-text-primary font-medium">{result.mean.toFixed(4)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Range</span>
                  <span className="text-text-primary font-medium">{result.min.toFixed(4)} – {result.max.toFixed(4)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Samples</span>
                  <span className="text-text-primary font-medium">{result.values.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Zone</span>
                  <span className="text-text-primary font-medium text-right max-w-[180px]">{result.label}</span>
                </div>
              </div>
            </Card>
          )}
        </div>

        <div className="lg:col-span-3 space-y-6">
          <Card padding="lg">
            <div className="flex items-center justify-between mb-4">
              <CardTitle>Distribution — {selected.toUpperCase()} at {city.name || `${city.lat.toFixed(2)}, ${city.lng.toFixed(2)}`}</CardTitle>
              {result && <Badge variant="success">ML Model</Badge>}
            </div>
            {result ? (
              <HistogramChart data={result.values} className="h-80 w-full" color={selected === 'ndvi' ? '#00C896' : selected === 'ndbi' ? '#F6C343' : '#3B82F6'} />
            ) : (
              <div className="h-80 flex items-center justify-center text-sm text-text-secondary border border-dashed border-border rounded-lg">
                Computing index for this location...
              </div>
            )}
          </Card>

          <Card padding="none" className="overflow-hidden">
            <CanvasHeatmap lat={city.lat} lng={city.lng} cityName={city.name} className="h-[300px]" />
          </Card>
        </div>
      </div>
    </div>
  );
}
