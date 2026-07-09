import { useState, useMemo, useEffect, useCallback } from 'react';
import { Card, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { FeatureImportanceChart } from '@/components/charts/FeatureImportanceChart';
import { useAppState } from '@/store/AppState';
import { computeXAIModel } from '@/services/xaiModel';
import { Brain, CheckCircle2, XCircle } from 'lucide-react';
import { LOCATIONS } from '@/services/locations';

export default function ModelExplainability() {
  const [computing, setComputing] = useState(false);
  const [result, setResult] = useState<{
    feature_importance: Record<string, number>;
    top_features: Array<{ name: string; importance: number }>;
    confidence: { overall: number; prediction: number; explanation: number };
    uncertainty: { overall: number; aleatoric: number; epistemic: number };
    accuracy: number; rSquared: number; valMAE: number; modelName: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { state } = useAppState();

  const [cityIdx, setCityIdx] = useState(() => {
    const idx = LOCATIONS.findIndex(c => Math.abs(c.lat - (state.selectedLocation?.lat ?? 0)) < 0.5 && Math.abs(c.lng - (state.selectedLocation?.lng ?? 0)) < 0.5);
    return idx >= 0 ? idx : 1;
  });

  const city = LOCATIONS[cityIdx];

  const runExplanation = useCallback(async () => {
    setComputing(true); setError(null);
    try {
      const res = await computeXAIModel(city.lat, city.lng, city.name);
      setResult(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setComputing(false);
    }
  }, [city.lat, city.lng, city.name]);

  useEffect(() => { runExplanation(); }, [cityIdx]);

  const featureData = useMemo(() => {
    if (!result?.top_features) return [];
    return result.top_features.map((f) => ({ feature: f.name, importance: f.importance }));
  }, [result]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Model Explainability</h1>
          <p className="text-sm text-text-secondary mt-0.5">Understand how ML models make predictions</p>
        </div>
        <Button onClick={runExplanation} loading={computing}>
          <Brain className="h-3.5 w-3.5" /> Explain Predictions
        </Button>
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

      {result && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { label: 'Overall Confidence', value: `${((result.confidence?.overall ?? 0) * 100).toFixed(0)}%`, color: '#00C896', detail: 'Model confidence score' },
            { label: 'Top Features', value: String(result.top_features?.length ?? 0), color: '#3B82F6', detail: 'Key predictive features' },
            { label: 'Uncertainty', value: `${((result.uncertainty?.overall ?? 0) * 100).toFixed(0)}%`, color: '#F6C343', detail: 'Prediction uncertainty' },
          ].map((s) => (
            <div key={s.label} className="stat-card">
              <div className="flex items-center gap-3">
                <p className="text-xl font-bold text-text-primary">{s.value}</p>
              </div>
              <p className="text-xs text-text-secondary mt-0.5">{s.label}</p>
              <div className="mt-2 h-1 rounded-full bg-white/5 overflow-hidden">
                <div className="h-full rounded-full transition-all" style={{ width: s.value, backgroundColor: s.color }} />
              </div>
            </div>
          ))}
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

      {error && (
        <Card padding="lg" className="border-warning/30">
          <div className="flex items-center gap-2 text-warning">
            <span className="text-xs">{error}</span>
          </div>
        </Card>
      )}

      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card padding="lg">
            <CardTitle>Feature Importance</CardTitle>
            {featureData.length > 0 ? (
              <FeatureImportanceChart data={featureData} className="h-72 w-full mt-2" />
            ) : (
              <div className="h-72 flex items-center justify-center text-sm text-text-secondary">No data</div>
            )}
          </Card>

          <Card padding="lg">
            <CardTitle>Feature Breakdown</CardTitle>
            <div className="space-y-3 mt-4">
              {result.top_features?.map((f, i) => (
                <div key={f.name}>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-text-primary">{f.name}</span>
                    <span className="font-medium text-text-primary">{(f.importance * 100).toFixed(0)}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${f.importance * 100}%`, background: i === 0 ? '#00C896' : i === 1 ? '#3B82F6' : i === 2 ? '#F6C343' : '#94A3B8' }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {!result && !error && !computing && (
        <Card padding="lg" className="text-center py-12">
          <div className="w-12 h-12 rounded-xl bg-accent/10 flex items-center justify-center mx-auto mb-4">
            <Brain className="h-6 w-6 text-accent" />
          </div>
          <p className="text-sm font-medium text-text-primary mb-1">No explanations yet</p>
          <p className="text-xs text-text-secondary mb-4">Run ML model explainability to understand feature impacts</p>
          <Button onClick={runExplanation} size="sm">
            <Brain className="h-3.5 w-3.5" /> Explain Predictions
          </Button>
        </Card>
      )}
    </div>
  );
}
