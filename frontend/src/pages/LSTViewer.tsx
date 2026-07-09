import { useState, useEffect, useMemo } from 'react';
import { Card, CardTitle } from '@/components/ui/Card';
import { Select } from '@/components/ui/Select';
import { CanvasHeatmap } from '@/components/map/CanvasHeatmap';
import { TemperatureTrendChart } from '@/components/charts/TemperatureTrendChart';
import { HistogramChart } from '@/components/charts/HistogramChart';
import { useLocationParams } from '@/hooks/useLocationParams';
import { computeLSTModel } from '@/services/lstModel';
import { Thermometer, TrendingUp, Brain, CheckCircle2, XCircle } from 'lucide-react';
import { LOCATIONS } from '@/services/locations';

export default function LSTViewer() {
  const loc = useLocationParams();
  const [stats, setStats] = useState<{
    current: number; mean: number; max: number; min: number;
    values: number[]; predicted: number[];
    accuracy: number; rSquared: number; valMAE: number; modelName: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState('30d');

  const [cityIdx, setCityIdx] = useState(() => {
    const idx = LOCATIONS.findIndex(c => Math.abs(c.lat - loc.lat) < 0.5 && Math.abs(c.lng - loc.lng) < 0.5);
    return idx >= 0 ? idx : 1;
  });

  const city = LOCATIONS[cityIdx];

  useEffect(() => {
    setLoading(true);
    computeLSTModel(city.lat, city.lng, city.name, parseInt(dateRange)).then((d) => {
      setStats(d);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [city.lat, city.lng, city.name, dateRange]);

  const trendData = useMemo(() => {
    if (!stats?.values) return [];
    return stats.values.map((v, i) => ({
      date: new Date(Date.now() - (stats.values.length - 1 - i) * 86400000).toLocaleDateString('en', { month: 'short', day: 'numeric' }),
      temperature: v,
    }));
  }, [stats]);

  const forecastData = useMemo(() => {
    if (!stats?.predicted?.length) return [];
    return stats.predicted.map((v, i) => {
      const d = new Date(Date.now());
      d.setDate(d.getDate() + i + 1);
      return {
        date: d.toLocaleDateString('en', { month: 'short', day: 'numeric' }),
        temperature: v,
      };
    });
  }, [stats]);

  const currentValue = stats?.current?.toFixed(2) ?? '—';
  const meanValue = stats?.mean?.toFixed(2) ?? '—';
  const maxValue = stats?.max?.toFixed(2) ?? '—';
  const minValue = stats?.min?.toFixed(2) ?? '—';

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">LST Viewer</h1>
          <p className="text-sm text-text-secondary mt-0.5">ML-powered Land Surface Temperature analysis</p>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="stat-card">
            <div className="flex items-center gap-2 mb-1">
              <Brain className="h-3.5 w-3.5 text-accent" />
              <span className="text-xs text-text-secondary uppercase tracking-wider">Model</span>
            </div>
            <p className="text-sm font-bold text-text-primary truncate">{stats.modelName}</p>
          </div>
          <div className="stat-card">
            <p className="text-2xs text-text-secondary uppercase tracking-wider mb-1">R² Score</p>
            <p className="text-lg font-bold text-text-primary">{stats.rSquared.toFixed(3)}</p>
          </div>
          <div className="stat-card">
            <p className="text-2xs text-text-secondary uppercase tracking-wider mb-1">Accuracy</p>
            <p className="text-lg font-bold text-text-primary">{stats.accuracy.toFixed(1)}%</p>
            <div className="flex items-center gap-1 text-2xs">
              {stats.accuracy >= 95 ? (
                <><CheckCircle2 className="h-3 w-3 text-success" /> 95%+ target met</>
              ) : (
                <><XCircle className="h-3 w-3 text-warning" /> below 95%</>
              )}
            </div>
          </div>
          <div className="stat-card">
            <p className="text-2xs text-text-secondary uppercase tracking-wider mb-1">Val MAE</p>
            <p className="text-lg font-bold text-text-primary">{stats.valMAE}°C</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Current LST', value: `${currentValue}°C`, color: '#FF5C72' },
          { label: 'Mean LST', value: `${meanValue}°C`, color: '#F6C343' },
          { label: 'Max LST', value: `${maxValue}°C`, color: '#FF5C72' },
          { label: 'Min LST', value: `${minValue}°C`, color: '#3B82F6' },
        ].map((s) => (
          <div key={s.label} className="stat-card">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${s.color}15` }}>
                <Thermometer className="h-4 w-4" style={{ color: s.color }} />
              </div>
              <div>
                <p className="text-xl font-bold text-text-primary tracking-tight">{s.value}</p>
                <p className="text-xs text-text-secondary">{s.label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 space-y-6">
          <Card padding="lg">
            <CardTitle>Temperature Trend</CardTitle>
            {trendData.length > 0 ? (
              <TemperatureTrendChart data={trendData} data2={forecastData} className="h-80 w-full mt-2" />
            ) : (
              <div className="h-80 flex items-center justify-center text-sm text-text-secondary">Loading data...</div>
            )}
            {forecastData.length > 0 && (
              <p className="text-xs text-text-secondary mt-2 flex items-center gap-1">
                <TrendingUp className="h-3 w-3" />
                7-day forecast based on Fourier+Seasonal+Lag ML model
              </p>
            )}
          </Card>

          <Card padding="lg">
            <CardTitle>Temperature Distribution</CardTitle>
            {stats?.values && stats.values.length > 0 ? (
              <HistogramChart data={stats.values} className="h-64 w-full mt-2" color="#00C896" />
            ) : (
              <div className="h-64 flex items-center justify-center text-sm text-text-secondary">Loading data...</div>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <Card padding="lg">
            <CardTitle className="mb-4">Controls</CardTitle>
            <div className="space-y-4">
              <Select label="City" value={String(cityIdx)} onChange={(e) => setCityIdx(Number(e.target.value))} options={LOCATIONS.map((c, i) => ({ value: String(i), label: c.name }))} />
              <Select label="Date Range" value={dateRange} onChange={(e) => setDateRange(e.target.value)} options={[
                { value: '7', label: 'Last 7 days' },
                { value: '30', label: 'Last 30 days' },
                { value: '90', label: 'Last 3 months' },
                { value: '365', label: 'Last year' },
              ]} />
              {loading && (
                <div className="flex items-center gap-2 text-xs text-text-secondary">
                  <div className="animate-spin w-3 h-3 border border-primary border-t-transparent rounded-full" />
                  Fetching 3 years of training data...
                </div>
              )}
            </div>
          </Card>

          <Card padding="none" className="overflow-hidden">
            <CanvasHeatmap lat={city.lat} lng={city.lng} cityName={city.name} className="h-[240px]" />
          </Card>
        </div>
      </div>
    </div>
  );
}
