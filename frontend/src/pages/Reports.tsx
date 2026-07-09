import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { CanvasHeatmap } from '@/components/map/CanvasHeatmap';
import { useLocationParams } from '@/hooks/useLocationParams';
import { useAppState } from '@/store/AppState';
import { generateReportModel } from '@/services/reportModel';
import { exportCSV, exportPDF, type PDFReportData } from '@/services/reports';
import { FileText, Download, File as FileIcon, Upload, Brain, CheckCircle2, XCircle } from 'lucide-react';
import { LOCATIONS } from '@/services/locations';

interface Report {
  id: string; title: string; type: string; createdAt: string;
  status: 'generated' | 'pending' | 'failed';
  summary: string; stats: Record<string, number>;
  modelInfo: { accuracy: number; rSquared: number; valMAE: number; modelName: string };
}

export default function Reports() {
  const navigate = useNavigate();
  const { state } = useAppState();
  const loc = useLocationParams();
  const [generating, setGenerating] = useState(false);
  const [dateRange, setDateRange] = useState('30d');
  const [reports, setReports] = useState<Report[]>([]);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [error, setError] = useState('');

  const [cityIdx, setCityIdx] = useState(() => {
    const idx = LOCATIONS.findIndex(
      c => Math.abs(c.lat - loc.lat) < 0.5 && Math.abs(c.lng - loc.lng) < 0.5
    );
    return idx >= 0 ? idx : 1;
  });

  const city = LOCATIONS[cityIdx];
  const hasData = state.uploadedFiles.length > 0;

  const generateReport = useCallback(async () => {
    setGenerating(true);
    setError('');
    try {
      const modelResult = await generateReportModel(city.lat, city.lng, city.name, state.uploadedFiles);
      const newReport: Report = {
        id: `RPT-${Math.round(Math.abs(city.lat * 1000 + city.lng * 1000))}`,
        title: `Urban Heat Analysis - ${city.name}`,
        type: 'Analysis',
        createdAt: new Date().toISOString(),
        status: 'generated',
        summary: `Analysis of ${modelResult.trainedDays} days of historical data for ${city.name}. Detected ${modelResult.hotspots} urban heat hotspots (${(modelResult.hotspots / 90 * 100).toFixed(1)}% anomaly rate) with ${modelResult.confidence > 0.8 ? 'high' : 'moderate'} confidence. Model R²=${modelResult.rSquared.toFixed(3)}, MAE=${modelResult.valMAE}°C.`,
        stats: modelResult.stats,
        modelInfo: {
          accuracy: modelResult.accuracy,
          rSquared: modelResult.rSquared,
          valMAE: modelResult.valMAE,
          modelName: modelResult.modelName,
        },
      };
      setReports((prev) => [newReport, ...prev]);
      setSelectedReport(newReport);
    } catch (e) {
      setError((e as Error).message);
    }
    setGenerating(false);
  }, [city.lat, city.lng, city.name, state.uploadedFiles]);

  useEffect(() => {
    generateReport();
  }, [cityIdx]);

  const handleExportPDF = (report: Report) => {
    const pdfData: PDFReportData = {
      title: report.title,
      cityName: city.name,
      createdAt: report.createdAt,
      summary: report.summary,
      stats: report.stats,
      modelInfo: report.modelInfo,
    };
    exportPDF(pdfData);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Reports</h1>
          <p className="text-sm text-text-secondary mt-0.5">ML-powered analysis report generation</p>
        </div>
        <div className="flex gap-2">
          <Select value={dateRange} onChange={(e) => setDateRange(e.target.value)} options={[
            { value: '7d', label: 'Last 7 days' }, { value: '30d', label: 'Last 30 days' },
            { value: '90d', label: 'Last 3 months' }, { value: '1y', label: 'Last year' },
          ]} />
          <Button
            onClick={hasData ? generateReport : () => navigate('/satellite')}
            loading={generating}
          >
            {hasData ? <FileText className="h-3.5 w-3.5" /> : <Upload className="h-3.5 w-3.5" />}
            {hasData ? 'Generate Report' : 'Upload Data First'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <Card padding="lg">
            <CardTitle className="mb-4">Parameters</CardTitle>
            <Select label="City" value={String(cityIdx)} onChange={(e) => setCityIdx(Number(e.target.value))} options={LOCATIONS.map((c, i) => ({ value: String(i), label: c.name }))} />
          </Card>

          <Card padding="lg">
            <CardTitle className="mb-4">Report History</CardTitle>
            {reports.length === 0 ? (
              <div className="text-center py-8 text-text-secondary">
                <FileIcon className="h-8 w-8 mx-auto mb-2 opacity-30" />
                <p className="text-xs">Generating report...</p>
              </div>
            ) : (
              <div className="space-y-1.5">
                {reports.map((r) => (
                  <div
                    key={r.id}
                    onClick={() => setSelectedReport(r)}
                    className={`p-3 rounded-lg cursor-pointer transition-all ${
                      selectedReport?.id === r.id
                        ? 'bg-accent/5 border border-accent/20'
                        : 'bg-surface-200/50 border border-transparent hover:bg-surface-200/80'
                    }`}
                  >
                    <p className="text-sm font-medium text-text-primary truncate">{r.title}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant={r.status === 'generated' ? 'success' : r.status === 'pending' ? 'info' : 'danger'}>
                        {r.status}
                      </Badge>
                      <span className="text-2xs text-text-secondary">{new Date(r.createdAt).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        <div className="lg:col-span-2">
          {error && (
            <div className="mb-4 p-4 rounded-xl bg-warning/10 border border-warning/20 text-sm text-text-primary">
              Model error: {error}
            </div>
          )}

          {selectedReport ? (
            <Card padding="lg">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <CardTitle>{selectedReport.title}</CardTitle>
                  <p className="text-xs text-text-secondary mt-1">
                    Generated {new Date(selectedReport.createdAt).toLocaleString()}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => handleExportPDF(selectedReport)}>
                    <Download className="h-3.5 w-3.5" /> PDF
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => exportCSV('report_stats', Object.entries(selectedReport.stats).map(([k, v]) => ({ metric: k, value: v })))}>
                    <Download className="h-3.5 w-3.5" /> CSV
                  </Button>
                </div>
              </div>

              {selectedReport.modelInfo && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
                  <div className="p-2.5 rounded-lg bg-accent/5 border border-accent/10">
                    <div className="flex items-center gap-1.5 mb-1">
                      <Brain className="h-3 w-3 text-accent" />
                      <span className="text-2xs text-text-secondary uppercase tracking-wider">Model</span>
                    </div>
                    <p className="text-xs font-bold text-text-primary truncate">{selectedReport.modelInfo.modelName}</p>
                  </div>
                  <div className="p-2.5 rounded-lg bg-surface-200/50 border border-border">
                    <p className="text-2xs text-text-secondary uppercase tracking-wider mb-0.5">R² Score</p>
                    <p className="text-base font-bold text-text-primary">{selectedReport.modelInfo.rSquared.toFixed(3)}</p>
                  </div>
                  <div className="p-2.5 rounded-lg bg-surface-200/50 border border-border">
                    <p className="text-2xs text-text-secondary uppercase tracking-wider mb-0.5">Accuracy</p>
                    <p className="text-base font-bold text-text-primary">{selectedReport.modelInfo.accuracy.toFixed(1)}%</p>
                    {selectedReport.modelInfo.accuracy >= 95 ? (
                      <CheckCircle2 className="h-3 w-3 text-success mt-0.5" />
                    ) : (
                      <XCircle className="h-3 w-3 text-warning mt-0.5" />
                    )}
                  </div>
                  <div className="p-2.5 rounded-lg bg-surface-200/50 border border-border">
                    <p className="text-2xs text-text-secondary uppercase tracking-wider mb-0.5">Val MAE</p>
                    <p className="text-base font-bold text-text-primary">{selectedReport.modelInfo.valMAE}°C</p>
                  </div>
                </div>
              )}

              <div className="space-y-5">
                <div className="p-4 rounded-lg bg-surface-200/50 border border-border">
                  <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Summary</h4>
                  <p className="text-sm text-text-primary">{selectedReport.summary}</p>
                </div>

                <div>
                  <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">Key Statistics</h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {Object.entries(selectedReport.stats).map(([key, val]) => (
                      <div key={key} className="p-3 rounded-lg bg-surface-200/50 border border-border text-center">
                        <p className="text-lg font-bold text-text-primary">
                          {typeof val === 'number' ? (val > 100 ? val.toFixed(0) : val.toFixed(2)) : val}
                        </p>
                        <p className="text-2xs text-text-secondary capitalize mt-0.5">{key.replace(/([A-Z])/g, ' $1').trim()}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl overflow-hidden border border-border">
                  <CanvasHeatmap lat={city.lat} lng={city.lng} cityName={city.name} className="h-[280px] rounded-none" />
                </div>
              </div>
            </Card>
          ) : (
            <Card padding="lg" className="text-center py-12">
              <div className="w-12 h-12 rounded-xl bg-accent/10 flex items-center justify-center mx-auto mb-4">
                {hasData ? <FileText className="h-6 w-6 text-accent" /> : <Upload className="h-6 w-6 text-accent" />}
              </div>
              <p className="text-sm font-medium text-text-primary mb-1">{hasData ? 'Select or generate a report' : 'No data uploaded'}</p>
              <p className="text-xs text-text-secondary mb-4">{hasData ? 'Choose from history or generate a new one' : 'Upload a dataset first to generate reports'}</p>
              <Button onClick={hasData ? generateReport : () => navigate('/satellite')} loading={generating} size="sm">
                {hasData ? <FileText className="h-3.5 w-3.5" /> : <Upload className="h-3.5 w-3.5" />}
                {hasData ? 'Generate Report' : 'Upload Data'}
              </Button>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
