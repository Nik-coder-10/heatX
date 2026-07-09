import { useState, useMemo, useEffect, useCallback } from 'react';
import { Card, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { TemperatureTrendChart } from '@/components/charts/TemperatureTrendChart';
import { useLocationParams } from '@/hooks/useLocationParams';
import { trainAndForecast, ForecastResult } from '@/services/forecastModel';
import { exportCSV, exportPDF, type PDFReportData } from '@/services/reports';
import { TrendingUp, Download, Brain, CheckCircle2, XCircle } from 'lucide-react';
import { LOCATIONS } from '@/services/locations';

export default function Forecasting() {
  const loc = useLocationParams();
  const [horizon, setHorizon] = useState('30');
  const [cityIdx, setCityIdx] = useState(() => {
    const idx = LOCATIONS.findIndex(
      c => Math.abs(c.lat - loc.lat) < 0.5 && Math.abs(c.lng - loc.lng) < 0.5
    );
    return idx >= 0 ? idx : 1;
  });
  const [forecasting, setForecasting] = useState(false);
  const [result, setResult] = useState<ForecastResult | null>(null);
  const [error, setError] = useState('');

  const city = LOCATIONS[cityIdx];

  const runForecast = useCallback(async () => {
    setForecasting(true);
    setError('');
    try {
      const data = await trainAndForecast(city.lat, city.lng, city.name, parseInt(horizon));
      setResult(data);
    } catch (e) {
      setError((e as Error).message);
    }
    setForecasting(false);
  }, [cityIdx, horizon, city.lat, city.lng, city.name]);

  useEffect(() => {
    runForecast();
  }, [cityIdx]);

  const chartData = useMemo(() => {
    if (!result) return [];
    return result.historical.map((t, i) => ({
      date: new Date(Date.now() - (result.historical.length - 1 - i) * 86400000)
        .toLocaleDateString('en', { month: 'short', day: 'numeric' }),
      temperature: t,
    }));
  }, [result]);

  const forecastData = useMemo(() => {
    if (!result) return [];
    return result.predicted.map((t, i) => ({
      date: new Date(Date.now() + (i + 1) * 86400000)
        .toLocaleDateString('en', { month: 'short', day: 'numeric' }),
      temperature: t,
    }));
  }, [result]);

  const predictedMean = result?.predicted.length
    ? (result.predicted.reduce((a, b) => a + b, 0) / result.predicted.length).toFixed(2)
    : '—';
  const predictedPeak = result?.predicted.length
    ? Math.max(...result.predicted).toFixed(2)
    : '—';
  const predictedMin = result?.predicted.length
    ? Math.min(...result.predicted).toFixed(2)
    : '—';

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Forecasting</h1>
          <p className="text-sm text-text-secondary mt-0.5">AI-powered temperature prediction model</p>
        </div>
        <div className="flex gap-2">
          {result && (
            <>
              <Button variant="outline" size="sm" onClick={() => exportCSV('forecast', chartData)}><Download className="h-3.5 w-3.5" /> CSV</Button>
              <Button variant="outline" size="sm" onClick={() => {
                const pdfData: PDFReportData = {
                  title: `Temperature Forecast - ${city.name}`,
                  cityName: city.name,
                  createdAt: new Date().toISOString(),
                  summary: `Forecast for ${city.name}: ${horizon}-day horizon. Predicted mean: ${predictedMean}°C, peak: ${predictedPeak}°C, min: ${predictedMin}°C. Model: ${result?.modelName || 'Fourier+ARIMA'}. R²: ${result?.rSquared?.toFixed(3) || 'N/A'}, MAE: ${result?.valMAE?.toFixed(1) || 'N/A'}°C.`,
                  stats: {
                    predictedMean: Number(predictedMean),
                    predictedPeak: Number(predictedPeak),
                    predictedMin: Number(predictedMin),
                    horizon: parseInt(horizon),
                    accuracy: result?.accuracy || 0,
                    rSquared: result?.rSquared || 0,
                    valMAE: result?.valMAE || 0,
                  },
                  modelInfo: {
                    modelName: result?.modelName || 'Fourier+ARIMA',
                    rSquared: result?.rSquared || 0,
                    accuracy: result?.accuracy || 0,
                    valMAE: result?.valMAE || 0,
                  },
                };
                exportPDF(pdfData);
              }}><Download className="h-3.5 w-3.5" /> PDF</Button>
            </>
          )}
          <Button onClick={runForecast} loading={forecasting}>
            <TrendingUp className="h-3.5 w-3.5" /> Train & Forecast
          </Button>
        </div>
      </div>

      {result && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          <div className="stat-card col-span-1">
            <div className="flex items-center gap-2 mb-1">
              <Brain className="h-3.5 w-3.5 text-accent" />
              <span className="text-xs text-text-secondary uppercase tracking-wider">Model</span>
            </div>
            <p className="text-lg font-bold text-text-primary">{result.modelName}</p>
          </div>
          <div className="stat-card">
            <p className="text-2xs text-text-secondary uppercase tracking-wider mb-1">Trained On</p>
            <p className="text-lg font-bold text-text-primary">{result.trainedDays}</p>
            <p className="text-2xs text-text-secondary">days of data</p>
          </div>
          <div className="stat-card">
            <p className="text-2xs text-text-secondary uppercase tracking-wider mb-1">R² Score</p>
            <p className="text-lg font-bold text-text-primary">{result.rSquared.toFixed(3)}</p>
            <p className="text-2xs text-secondary">variance explained</p>
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
            <p className="text-2xs text-secondary">mean absolute error</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: 'Forecast Horizon', value: `${horizon} days` },
          { label: 'Data Points', value: result ? `${result.historical.length + result.predicted.length}` : '—' },
          { label: 'City', value: city.name },
        ].map((s) => (
          <div key={s.label} className="stat-card">
            <p className="text-xl font-bold text-text-primary">{s.value}</p>
            <p className="text-xs text-text-secondary mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3">
          <Card padding="lg">
            <CardTitle>Temperature Projection</CardTitle>
            {result ? (
              <TemperatureTrendChart data={chartData} data2={forecastData} className="h-80 w-full mt-2" />
            ) : error ? (
              <div className="h-80 flex items-center justify-center text-sm text-text-secondary border border-dashed border-border rounded-lg mt-2">
                Error: {error}
              </div>
            ) : (
              <div className="h-80 flex items-center justify-center text-sm text-text-secondary border border-dashed border-border rounded-lg mt-2">
                Training model... fetching 3 years of data
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <Card padding="lg">
            <CardTitle className="mb-4">Parameters</CardTitle>
            <div className="space-y-4">
              <Select label="City" value={String(cityIdx)} onChange={(e) => setCityIdx(Number(e.target.value))} options={LOCATIONS.map((c, i) => ({ value: String(i), label: c.name }))} />
              <Select label="Forecast Horizon" value={horizon} onChange={(e) => setHorizon(e.target.value)} options={[
                { value: '7', label: '7 days' },
                { value: '14', label: '14 days' },
                { value: '30', label: '30 days' },
                { value: '90', label: '90 days' },
              ]} />
              <Button className="w-full" onClick={runForecast} loading={forecasting}>
                <TrendingUp className="h-3.5 w-3.5" /> Train & Generate
              </Button>
            </div>
          </Card>

          {result && (
            <Card padding="lg">
              <CardTitle className="mb-3">Projected Stats</CardTitle>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-text-secondary">Mean</span>
                  <span className="text-text-primary font-medium">{predictedMean}°C</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Peak</span>
                  <span className="text-text-primary font-medium">{predictedPeak}°C</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Min</span>
                  <span className="text-text-primary font-medium">{predictedMin}°C</span>
                </div>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
