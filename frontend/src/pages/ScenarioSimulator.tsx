import { useState, useMemo, useEffect, useCallback } from 'react';
import { Card, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { Slider } from '@/components/ui/Slider';
import { ScenarioComparisonChart } from '@/components/charts/ScenarioComparisonChart';
import { TemperatureTrendChart } from '@/components/charts/TemperatureTrendChart';
import { useLocationParams } from '@/hooks/useLocationParams';
import { runScenarioModel } from '@/services/scenarioModel';
import { exportScenarioResults } from '@/services/reports';
import { Beaker, Trees, Building2, FlaskConical, Download, Brain, CheckCircle2, XCircle } from 'lucide-react';
import { LOCATIONS } from '@/services/locations';
import type { SimulationResult } from '@/types';

interface ScenarioControl {
  id: string; label: string; icon: React.ComponentType<{ className?: string }>;
  intensity: number; active: boolean; color: string;
}

const DEFAULT_SCENARIOS: ScenarioControl[] = [
  { id: 'trees', label: 'Tree Planting', icon: Trees, intensity: 0.5, active: true, color: '#00C896' },
  { id: 'roofs', label: 'Cool Roofs', icon: Building2, intensity: 0.4, active: true, color: '#3B82F6' },
  { id: 'parks', label: 'Green Parks', icon: Trees, intensity: 0.3, active: true, color: '#10B981' },
  { id: 'water', label: 'Water Features', icon: FlaskConical, intensity: 0.2, active: false, color: '#F6C343' },
];

export default function ScenarioSimulator() {
  const loc = useLocationParams();
  const [scenarios, setScenarios] = useState<ScenarioControl[]>(DEFAULT_SCENARIOS);
  const [simulating, setSimulating] = useState(false);
  const [results, setResults] = useState<SimulationResult[]>([]);
  const [error, setError] = useState('');
  const [modelInfo, setModelInfo] = useState<{ accuracy: number; rSquared: number; valMAE: number; modelName: string; cityName: string } | null>(null);

  const [cityIdx, setCityIdx] = useState(() => {
    const idx = LOCATIONS.findIndex(
      c => Math.abs(c.lat - loc.lat) < 0.5 && Math.abs(c.lng - loc.lng) < 0.5
    );
    return idx >= 0 ? idx : 1;
  });

  const city = LOCATIONS[cityIdx];

  const updateIntensity = (id: string, intensity: number) => {
    setScenarios((prev) => prev.map((s) => s.id === id ? { ...s, intensity } : s));
  };

  const toggleScenario = (id: string) => {
    setScenarios((prev) => prev.map((s) => s.id === id ? { ...s, active: !s.active } : s));
  };

  const activeCount = scenarios.filter((s) => s.active).length;

  const runSimulation = useCallback(async () => {
    setSimulating(true);
    setError('');
    try {
      const modelResult = await runScenarioModel(city.lat, city.lng, city.name, scenarios);
      setResults(modelResult.simulations);
      setModelInfo({
        accuracy: modelResult.accuracy,
        rSquared: modelResult.rSquared,
        valMAE: modelResult.valMAE,
        modelName: modelResult.modelName,
        cityName: modelResult.cityName,
      });
    } catch (e) {
      setError((e as Error).message);
    }
    setSimulating(false);
  }, [city.lat, city.lng, city.name, scenarios]);

  useEffect(() => {
    runSimulation();
  }, [cityIdx]);

  const chartData = useMemo(() => results.map((r) => ({
    name: r.scenario_name,
    tempReduction: Math.abs(r.mean_lst_change),
    cost: r.estimated_cost,
    costEffectiveness: r.cost_effectiveness,
  })), [results]);

  const trendData = useMemo(() => {
    if (results.length === 0) return [];
    const base = results.reduce((a, r) => a + r.mean_lst_simulated, 0) / results.length;
    return Array.from({ length: 14 }, (_, i) => ({
      date: new Date(Date.now() - (13 - i) * 86400000).toLocaleDateString('en', { month: 'short', day: 'numeric' }),
      temperature: Number((base + Math.sin(i * 0.5) * 1.5).toFixed(2)),
    }));
  }, [results]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Scenario Simulator</h1>
          <p className="text-sm text-text-secondary mt-0.5">ML-powered mitigation strategy simulation</p>
        </div>
        <div className="flex gap-2">
          {results.length > 0 && (
            <Button variant="outline" size="sm" onClick={() => exportScenarioResults(results)}>
              <Download className="h-3.5 w-3.5" /> Export
            </Button>
          )}
          <Button onClick={runSimulation} loading={simulating} disabled={activeCount === 0}>
            <Beaker className="h-3.5 w-3.5" /> Run Simulation
          </Button>
        </div>
      </div>

      {modelInfo && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="stat-card col-span-1">
            <div className="flex items-center gap-2 mb-1">
              <Brain className="h-3.5 w-3.5 text-accent" />
              <span className="text-xs text-text-secondary uppercase tracking-wider">Model</span>
            </div>
            <p className="text-sm font-bold text-text-primary truncate">{modelInfo.modelName}</p>
          </div>
          <div className="stat-card">
            <p className="text-2xs text-text-secondary uppercase tracking-wider mb-1">R² Score</p>
            <p className="text-lg font-bold text-text-primary">{modelInfo.rSquared.toFixed(3)}</p>
            <p className="text-2xs text-secondary">variance explained</p>
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
            <p className="text-2xs text-secondary">mean absolute error</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="space-y-4">
          <Card padding="lg">
            <CardTitle className="mb-4">Configuration</CardTitle>
            <Select label="City" value={String(cityIdx)} onChange={(e) => setCityIdx(Number(e.target.value))} options={LOCATIONS.map((c, i) => ({ value: String(i), label: c.name }))} />
          </Card>

          {scenarios.map((s) => (
            <div
              key={s.id}
              className={`p-4 rounded-xl border transition-all cursor-pointer ${
                s.active ? 'border-accent/30 bg-accent/5' : 'border-border hover:border-white/10 bg-surface-200/50'
              }`}
              onClick={() => toggleScenario(s.id)}
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg flex items-center justify-center" style={{ backgroundColor: s.color + '20', color: s.color }}>
                  <s.icon className="h-4 w-4" />
                </div>
                <div className="flex-1">
                  <span className="text-sm font-medium text-text-primary">{s.label}</span>
                  {s.active && <Badge variant="success" className="ml-2">Active</Badge>}
                </div>
              </div>
              {s.active && (
                <Slider
                  label="Intensity"
                  value={s.intensity}
                  min={0} max={1} step={0.05}
                  onChange={(v) => updateIntensity(s.id, v)}
                  formatValue={(v) => `${(v * 100).toFixed(0)}%`}
                />
              )}
            </div>
          ))}
        </div>

        <div className="lg:col-span-2 space-y-6">
          {error && (
            <div className="p-4 rounded-xl bg-warning/10 border border-warning/20 text-sm text-text-primary">
              Model error: {error}
            </div>
          )}

          {results.length > 0 && !error ? (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                  { label: 'Scenarios', value: String(results.length), color: '#00C896' },
                  { label: 'Avg Reduction', value: results.length ? `${(results.reduce((a, r) => a + Math.abs(r.mean_lst_change), 0) / results.length).toFixed(2)}°C` : '—', color: '#3B82F6' },
                  { label: 'Total CO₂ Reduction', value: results.length ? `${results.reduce((a, r) => a + r.estimated_co2_reduction, 0).toFixed(0)}t` : '—', color: '#00C896' },
                  { label: 'Best Scenario', value: results.length ? results.reduce((a, r) => Math.abs(r.mean_lst_change) > Math.abs(a.mean_lst_change) ? r : a).scenario_name : '—', color: '#F6C343' },
                ].map((s) => (
                  <div key={s.label} className="stat-card">
                    <p className="text-lg font-bold text-text-primary">{s.value}</p>
                    <p className="text-xs text-text-secondary mt-0.5">{s.label}</p>
                  </div>
                ))}
              </div>

              <Card padding="lg">
                <CardTitle>Scenario Comparison</CardTitle>
                <ScenarioComparisonChart data={chartData} className="h-72 w-full mt-2" />
              </Card>

              <Card padding="lg">
                <CardTitle>Temperature Impact</CardTitle>
                <TemperatureTrendChart data={trendData} className="h-64 w-full mt-2" />
              </Card>
            </>
          ) : !error ? (
            <Card padding="lg" className="text-center py-12">
              <div className="w-12 h-12 rounded-xl bg-accent/10 flex items-center justify-center mx-auto mb-4">
                <Beaker className="h-6 w-6 text-accent" />
              </div>
              <p className="text-sm font-medium text-text-primary mb-1">No simulations yet</p>
              <p className="text-xs text-text-secondary mb-4">Configure scenarios and run a simulation</p>
              <Button onClick={runSimulation} size="sm" disabled={activeCount === 0}>
                <Beaker className="h-3.5 w-3.5" /> Run Simulation
              </Button>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
