import { useState, useMemo, useEffect } from 'react';
import { Card, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { DataTable, type Column } from '@/components/ui/DataTable';
import { CanvasHeatmap } from '@/components/map/CanvasHeatmap';
import { HistogramChart } from '@/components/charts/HistogramChart';
import { useLocationParams } from '@/hooks/useLocationParams';
import { detectUHIModel } from '@/services/uhiModel';
import { exportCSV } from '@/services/reports';
import { Flame, Download, Search, Brain, CheckCircle2, XCircle } from 'lucide-react';
import { LOCATIONS } from '@/services/locations';

interface HotspotRow {
  id: string; severity: string; temperature: number; area: number;
  confidence: number; ndvi: number; location: string;
}

export default function UrbanHeatViewer() {
  const loc = useLocationParams();
  const [detecting, setDetecting] = useState(false);
  const [hotspots, setHotspots] = useState<HotspotRow[]>([]);
  const [modelInfo, setModelInfo] = useState<{ accuracy: number; rSquared: number; valMAE: number; modelName: string } | null>(null);
  const [search, setSearch] = useState('');

  const [cityIdx, setCityIdx] = useState(() => {
    const idx = LOCATIONS.findIndex(c => Math.abs(c.lat - loc.lat) < 0.5 && Math.abs(c.lng - loc.lng) < 0.5);
    return idx >= 0 ? idx : 1;
  });

  const city = LOCATIONS[cityIdx];

  const runDetection = async () => {
    setDetecting(true);
    try {
      const result = await detectUHIModel(city.lat, city.lng, city.name);
      setHotspots(result.hotspots);
      setModelInfo({ accuracy: result.accuracy, rSquared: result.rSquared, valMAE: result.valMAE, modelName: result.modelName });
    } catch {
      setHotspots([]);
    }
    setDetecting(false);
  };

  useEffect(() => {
    if (hotspots.length === 0) runDetection();
  }, [city.lat, city.lng]);

  const filtered = useMemo(() => {
    if (!search.trim()) return hotspots;
    const q = search.toLowerCase();
    return hotspots.filter((h) =>
      h.id.toLowerCase().includes(q) || h.severity.toLowerCase().includes(q) || h.location.toLowerCase().includes(q)
    );
  }, [hotspots, search]);

  const stats = [
    { label: 'Hotspots Detected', value: hotspots.length, color: '#FF5C72', icon: Flame },
    { label: 'Avg Temperature', value: hotspots.length ? (hotspots.reduce((a, h) => a + h.temperature, 0) / hotspots.length).toFixed(2) : '—', color: '#F6C343', icon: Flame },
    { label: 'High Severity', value: hotspots.filter((h) => h.severity === 'High' || h.severity === 'Extreme').length, color: '#FF5C72', icon: Flame },
    { label: 'Avg Confidence', value: hotspots.length ? `${(hotspots.reduce((a, h) => a + h.confidence, 0) / hotspots.length * 100).toFixed(0)}%` : '—', color: '#00C896', icon: Flame },
  ];

  const columns: Column<HotspotRow>[] = [
    { key: 'id', header: 'ID' },
    { key: 'severity', header: 'Severity', render: (h) => <Badge variant={h.severity === 'Extreme' ? 'danger' : h.severity === 'High' ? 'warning' : 'info'}>{h.severity}</Badge> },
    { key: 'temperature', header: 'Temp (°C)', sortable: true },
    { key: 'area', header: 'Area (km²)', sortable: true },
    { key: 'confidence', header: 'Confidence', sortable: true, render: (h) => `${(h.confidence * 100).toFixed(0)}%` },
    { key: 'ndvi', header: 'NDVI', sortable: true },
    { key: 'location', header: 'Location' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Urban Heat Island Detection</h1>
          <p className="text-sm text-text-secondary mt-0.5">ML-powered hotspot detection</p>
        </div>
        <div className="flex gap-2">
          {hotspots.length > 0 && (
            <Button variant="outline" size="sm" onClick={() => exportCSV('hotspots', hotspots as unknown as Record<string, unknown>[])}>
              <Download className="h-3.5 w-3.5" /> CSV
            </Button>
          )}
          <Button onClick={runDetection} loading={detecting}>
            <Flame className="h-3.5 w-3.5" /> Run Detection
          </Button>
        </div>
      </div>

      {modelInfo && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="stat-card">
            <div className="flex items-center gap-2 mb-1">
              <Brain className="h-3.5 w-3.5 text-accent" />
              <span className="text-xs text-text-secondary uppercase tracking-wider">Model</span>
            </div>
            <p className="text-sm font-bold text-text-primary truncate">{modelInfo.modelName}</p>
          </div>
          <div className="stat-card">
            <p className="text-2xs text-text-secondary uppercase tracking-wider mb-1">R² Score</p>
            <p className="text-lg font-bold text-text-primary">{modelInfo.rSquared.toFixed(3)}</p>
          </div>
          <div className="stat-card">
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
          <div className="stat-card">
            <p className="text-2xs text-text-secondary uppercase tracking-wider mb-1">Val MAE</p>
            <p className="text-lg font-bold text-text-primary">{modelInfo.valMAE}°C</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="sm:col-span-1">
          <Card padding="lg">
            <CardTitle className="mb-3">City</CardTitle>
            <Select label="Location" value={String(cityIdx)} onChange={(e) => setCityIdx(Number(e.target.value))} options={LOCATIONS.map((c, i) => ({ value: String(i), label: c.name }))} />
          </Card>
        </div>
        <div className="sm:col-span-3">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {stats.map((s) => (
              <div key={s.label} className="stat-card">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${s.color}15` }}>
                    <s.icon className="h-4 w-4" style={{ color: s.color }} />
                  </div>
                  <div>
                    <p className="text-xl font-bold text-text-primary">{s.value}</p>
                    <p className="text-xs text-text-secondary">{s.label}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card padding="none" className="overflow-hidden">
          <CanvasHeatmap lat={city.lat} lng={city.lng} cityName={city.name} className="h-[350px]" />
        </Card>
        <Card padding="lg">
          <CardTitle>Temperature Distribution</CardTitle>
          {hotspots.length > 0 ? (
            <HistogramChart data={hotspots.map((h) => h.temperature)} className="h-72 w-full mt-2" color="#FF5C72" />
          ) : (
            <div className="h-72 flex items-center justify-center text-sm text-text-secondary">Run detection to see distribution</div>
          )}
        </Card>
      </div>

      {hotspots.length > 0 && (
        <Card padding="none">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <CardTitle>Hotspot Table</CardTitle>
            <div className="relative w-56">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-secondary" />
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search hotspots..." className="input-field pl-8 text-xs" />
            </div>
          </div>
          <DataTable columns={columns} data={filtered} />
        </Card>
      )}

      {hotspots.length === 0 && !detecting && (
        <Card padding="lg" className="text-center py-12">
          <div className="w-12 h-12 rounded-xl bg-accent/10 flex items-center justify-center mx-auto mb-4">
            <Flame className="h-6 w-6 text-accent" />
          </div>
          <p className="text-sm font-medium text-text-primary mb-1">No detection results yet</p>
          <p className="text-xs text-text-secondary mb-4">Run urban heat island detection to find hotspots</p>
          <Button onClick={runDetection} size="sm">
            <Flame className="h-3.5 w-3.5" /> Run Detection
          </Button>
        </Card>
      )}
    </div>
  );
}
