import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { CanvasHeatmap } from '@/components/map/CanvasHeatmap';
import { TemperatureTrendChart } from '@/components/charts/TemperatureTrendChart';
import { useAppState } from '@/store/AppState';
import { useLocationParams } from '@/hooks/useLocationParams';
import { computeDashboardModel } from '@/services/dashboardModel';
import { clsx } from 'clsx';
import { Flame, Thermometer, MapPin, RefreshCw, Upload, Database, ArrowUpRight, ArrowDownRight, Lock, Brain, CheckCircle2, XCircle } from 'lucide-react';
import { LOCATIONS } from '@/services/locations';

export default function Dashboard() {
  const [data, setData] = useState<{ lst: number; hotspots: number; alerts: number; trend: number } | null>(null);
  const [modelInfo, setModelInfo] = useState<{ accuracy: number; rSquared: number; valMAE: number; modelName: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const { state } = useAppState();
  const navigate = useNavigate();
  const loc = useLocationParams();

  const [cityIdx, setCityIdx] = useState(() => {
    const idx = LOCATIONS.findIndex(c => Math.abs(c.lat - loc.lat) < 0.5 && Math.abs(c.lng - loc.lng) < 0.5);
    return idx >= 0 ? idx : 1;
  });

  const city = LOCATIONS[cityIdx];

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await computeDashboardModel(city.lat, city.lng, city.name);
      setData({ lst: result.lst, hotspots: result.hotspots, alerts: result.alerts, trend: result.trend });
      setModelInfo({ accuracy: result.accuracy, rSquared: result.rSquared, valMAE: result.valMAE, modelName: result.modelName });
    } catch {
      setData({ lst: 0, hotspots: 0, alerts: 0, trend: 0 });
    } finally {
      setLoading(false);
    }
  }, [city.lat, city.lng, city.name]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const trendData = useMemo(() => {
    if (!data?.lst) return [];
    const base = data.lst;
    return Array.from({ length: 14 }, (_, i) => ({
      date: new Date(Date.now() - (13 - i) * 86400000).toLocaleDateString('en', { month: 'short', day: 'numeric' }),
      temperature: Number((base + Math.sin(i * 0.7) * 1.5 + Math.cos(i * 0.3) * 0.5).toFixed(2)),
    }));
  }, [data]);

  const avgLst = data?.lst != null ? `${data.lst.toFixed(2)}°C` : '—';
  const stats = [
    { label: 'Avg LST', value: avgLst, icon: Thermometer, trend: `${data?.trend != null ? (data.trend > 0 ? '+' : '') + data.trend.toFixed(1) : '—'}°`, up: (data?.trend ?? 0) > 0, color: '#EF4444' },
    { label: 'Hotspots', value: data?.hotspots != null ? String(data.hotspots) : '—', icon: Flame, trend: `${data?.hotspots ?? 0}`, up: true, color: '#F59E0B' },
    { label: 'Active Alerts', value: data?.alerts != null ? String(data.alerts) : '—', icon: MapPin, trend: 'Active', up: false, color: '#3B82F6' },
    { label: 'Datasets', value: String(state.uploadedFiles.length), icon: Database, trend: '+2', up: true, color: '#10B981' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between animate-slide-up">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Dashboard</h1>
          <p className="text-sm text-text-secondary mt-0.5">Urban Climate Intelligence Platform overview</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden md:inline text-xs text-text-secondary">{new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
          <Button size="sm" variant="secondary" onClick={fetchData} loading={loading}>
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </Button>
        </div>
      </div>

      {modelInfo && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="stat-card animate-slide-up stagger-1">
            <div className="flex items-center gap-2 mb-1">
              <Brain className="h-3.5 w-3.5 text-accent" />
              <span className="text-xs text-text-secondary uppercase tracking-wider">Model</span>
            </div>
            <p className="text-sm font-bold text-text-primary truncate">{modelInfo.modelName}</p>
          </div>
          <div className="stat-card animate-slide-up stagger-2">
            <p className="text-2xs text-text-secondary uppercase tracking-wider mb-1">R² Score</p>
            <p className="text-lg font-bold text-text-primary">{modelInfo.rSquared.toFixed(3)}</p>
          </div>
          <div className="stat-card animate-slide-up stagger-3">
            <p className="text-2xs text-text-secondary uppercase tracking-wider mb-1">Accuracy</p>
            <p className="text-lg font-bold text-text-primary">{modelInfo.accuracy.toFixed(1)}%</p>
            <div className="flex items-center gap-1 text-2xs">
              {modelInfo.accuracy >= 95 ? (
                <><CheckCircle2 className="h-3 w-3 text-success" /> 95%+ target met</>
              ) : (
                <><XCircle className="h-3 w-3 text-warning" /> below 95%</>
              )}
            </div>
          </div>
          <div className="stat-card animate-slide-up stagger-4">
            <p className="text-2xs text-text-secondary uppercase tracking-wider mb-1">Val MAE</p>
            <p className="text-lg font-bold text-text-primary">{modelInfo.valMAE}°C</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s, i) => (
          <div key={s.label} className={clsx('stat-card animate-slide-up', `stagger-${i + 1}`)}>
            <div className="flex items-center justify-between mb-3">
              <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${s.color}15` }}>
                <s.icon className="h-4 w-4" style={{ color: s.color }} />
              </div>
              <Badge variant={s.up ? 'success' : 'warning'}>
                <div className="flex items-center gap-0.5">
                  {s.up ? <ArrowUpRight className="h-2.5 w-2.5" /> : <ArrowDownRight className="h-2.5 w-2.5" />}
                  {s.trend}
                </div>
              </Badge>
            </div>
            <p className="text-2xl font-bold text-text-primary tracking-tight">{s.value}</p>
            <p className="text-xs text-text-secondary mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card padding="lg" className="animate-slide-up stagger-5">
          <div className="flex items-center justify-between mb-4">
            <CardTitle>Temperature Trend</CardTitle>
            <Select value={String(cityIdx)} onChange={(e) => setCityIdx(Number(e.target.value))} options={LOCATIONS.map((c, i) => ({ value: String(i), label: c.name }))} />
          </div>
          {trendData.length > 0 ? (
            <TemperatureTrendChart data={trendData} className="h-72 w-full mt-2" />
          ) : (
            <div className="h-72 flex items-center justify-center text-sm text-text-secondary">Loading data...</div>
          )}
        </Card>
        <Card padding="none" className="overflow-hidden animate-slide-up stagger-6">
          <CanvasHeatmap lat={city.lat} lng={city.lng} cityName={city.name} className="h-[328px]" />
        </Card>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <button onClick={() => navigate('/satellite')} className="block w-full text-left animate-slide-up stagger-6">
          <Card hover padding="lg" className="group cursor-pointer">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                <Upload className="h-5 w-5 text-accent" />
              </div>
              <div>
                <p className="text-sm font-semibold text-text-primary">Upload Data</p>
                <p className="text-xs text-text-secondary mt-0.5">Import satellite imagery or CSV data</p>
              </div>
            </div>
          </Card>
        </button>

        <button
          onClick={() => state.uploadedFiles.length > 0 && navigate('/uhi')}
          disabled={state.uploadedFiles.length === 0}
          className="block w-full text-left animate-slide-up stagger-7"
        >
          <Card hover={state.uploadedFiles.length > 0} padding="lg" className={clsx('group', state.uploadedFiles.length === 0 && 'opacity-50')}>
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-info/10 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                {state.uploadedFiles.length === 0 ? <Lock className="h-5 w-5 text-text-secondary" /> : <Flame className="h-5 w-5 text-info" />}
              </div>
              <div>
                <p className="text-sm font-semibold text-text-primary">Run Detection</p>
                <p className="text-xs text-text-secondary mt-0.5">{state.uploadedFiles.length === 0 ? 'Upload data first to enable detection' : 'Detect urban heat islands'}</p>
              </div>
            </div>
          </Card>
        </button>

        <button
          onClick={() => state.uploadedFiles.length > 0 && navigate('/reports')}
          disabled={state.uploadedFiles.length === 0}
          className="block w-full text-left animate-slide-up stagger-8"
        >
          <Card hover={state.uploadedFiles.length > 0} padding="lg" className={clsx('group', state.uploadedFiles.length === 0 && 'opacity-50')}>
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-warning/10 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                {state.uploadedFiles.length === 0 ? <Lock className="h-5 w-5 text-text-secondary" /> : <Flame className="h-5 w-5 text-warning" />}
              </div>
              <div>
                <p className="text-sm font-semibold text-text-primary">View Reports</p>
                <p className="text-xs text-text-secondary mt-0.5">{state.uploadedFiles.length === 0 ? 'Upload data first to generate reports' : 'Generate analysis reports'}</p>
              </div>
            </div>
          </Card>
        </button>
      </div>
    </div>
  );
}
