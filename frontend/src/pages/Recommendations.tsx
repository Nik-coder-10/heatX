import { useState, useMemo, useEffect, useCallback } from 'react';
import { Card, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { RecommendationRankingChart } from '@/components/charts/RecommendationRankingChart';
import { ScenarioComparisonChart } from '@/components/charts/ScenarioComparisonChart';
import { useAppState } from '@/store/AppState';
import { generateRecommendationModel } from '@/services/recommendationModel';
import { exportRecommendationCSV } from '@/services/reports';
import { Lightbulb, Thermometer, Download, Brain, CheckCircle2, XCircle } from 'lucide-react';
import { LOCATIONS } from '@/services/locations';
import type { ScoredRecommendation } from '@/types';

export default function Recommendations() {
  const [computing, setComputing] = useState(false);
  const [recs, setRecs] = useState<ScoredRecommendation[]>([]);
  const [modelInfo, setModelInfo] = useState<{ accuracy: number; rSquared: number; valMAE: number; modelName: string } | null>(null);
  const { state } = useAppState();

  const [cityIdx, setCityIdx] = useState(() => {
    const idx = LOCATIONS.findIndex(c => Math.abs(c.lat - (state.selectedLocation?.lat ?? 0)) < 0.5 && Math.abs(c.lng - (state.selectedLocation?.lng ?? 0)) < 0.5);
    return idx >= 0 ? idx : 1;
  });

  const city = LOCATIONS[cityIdx];

  const run = useCallback(async () => {
    setComputing(true);
    try {
      const result = await generateRecommendationModel(city.lat, city.lng, city.name);
      setRecs(result.recommendations);
      setModelInfo({ accuracy: result.accuracy, rSquared: result.rSquared, valMAE: result.valMAE, modelName: result.modelName });
    } catch {
      setRecs([]);
    } finally {
      setComputing(false);
    }
  }, [city.lat, city.lng, city.name]);

  useEffect(() => { run(); }, [cityIdx]);

  const chartData = useMemo(() => recs.map((r) => ({
    label: r.label.length > 20 ? r.label.slice(0, 20) + '...' : r.label,
    overallScore: r.overall_score,
    cost: r.estimated_cost,
  })), [recs]);

  const scenarioData = useMemo(() => recs.map((r) => ({
    name: r.label.length > 20 ? r.label.slice(0, 20) + '...' : r.label,
    tempReduction: r.expected_temperature_reduction,
    cost: r.estimated_cost,
    costEffectiveness: r.cost_effectiveness,
  })), [recs]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Recommendations</h1>
          <p className="text-sm text-text-secondary mt-0.5">ML-driven mitigation recommendations</p>
        </div>
        <div className="flex gap-2">
          {recs.length > 0 && (
            <Button variant="outline" size="sm" onClick={() => exportRecommendationCSV(recs)}>
              <Download className="h-3.5 w-3.5" /> CSV
            </Button>
          )}
          <Button onClick={run} loading={computing}>
            <Lightbulb className="h-3.5 w-3.5" /> Generate
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
      </div>

      {recs.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card padding="lg">
            <CardTitle>Recommendation Ranking</CardTitle>
            <RecommendationRankingChart data={chartData} className="h-80 w-full mt-2" />
          </Card>
          <Card padding="lg">
            <CardTitle>Temperature Reduction</CardTitle>
            <ScenarioComparisonChart data={scenarioData} metric="temp" className="h-80 w-full mt-2" />
          </Card>
        </div>
      )}

      {recs.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card padding="lg">
            <CardTitle>Cost Comparison</CardTitle>
            <ScenarioComparisonChart data={scenarioData} metric="cost" className="h-72 w-full mt-2" />
          </Card>
          <Card padding="lg">
            <CardTitle>Cost Effectiveness</CardTitle>
            <ScenarioComparisonChart data={scenarioData} metric="cost_effectiveness" className="h-72 w-full mt-2" />
          </Card>
        </div>
      )}

      {recs.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {recs.map((r) => (
            <Card key={r.label} padding="lg" hover>
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center flex-shrink-0">
                  <Lightbulb className="h-5 w-5 text-accent" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="text-sm font-semibold text-text-primary">{r.label}</h4>
                    <Badge variant={r.priority <= 2 ? 'danger' : r.priority === 3 ? 'warning' : 'info'}>
                      P{r.priority}
                    </Badge>
                  </div>
                  <p className="text-xs text-text-secondary mb-3">{r.description}</p>
                  <div className="flex flex-wrap gap-3 text-xs">
                    <span className="flex items-center gap-1 text-text-secondary">
                      <Thermometer className="h-3 w-3 text-danger" /> -{r.expected_temperature_reduction}°C
                    </span>
                    <span className="text-text-secondary">${(r.estimated_cost / 1_000_000).toFixed(2)}M</span>
                    <span className="text-text-secondary">Score: {r.overall_score.toFixed(2)}</span>
                    <span className="text-text-secondary">Feasibility: {(r.feasibility_score * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {recs.length === 0 && !computing && (
        <Card padding="lg" className="text-center py-12">
          <div className="w-12 h-12 rounded-xl bg-accent/10 flex items-center justify-center mx-auto mb-4">
            <Lightbulb className="h-6 w-6 text-accent" />
          </div>
          <p className="text-sm font-medium text-text-primary mb-1">No recommendations generated</p>
          <p className="text-xs text-text-secondary mb-4">Run analysis to get data-driven mitigation strategies</p>
          <Button onClick={run} size="sm">
            <Lightbulb className="h-3.5 w-3.5" /> Generate Recommendations
          </Button>
        </Card>
      )}
    </div>
  );
}
