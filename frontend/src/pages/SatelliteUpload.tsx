import { useMemo } from 'react';
import { Card, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { DragDropZone } from '@/components/ui/DragDropZone';
import { FileList } from '@/components/ui/FileList';
import { DataPreview } from '@/components/ui/DataPreview';
import { CanvasHeatmap } from '@/components/map/CanvasHeatmap';
import { useAppState } from '@/store/AppState';
import { exportCSV } from '@/services/reports';
import { Upload, Database, MapPin } from 'lucide-react';

export default function SatelliteUpload() {
  const { state, dispatch } = useAppState();


  const selectedFile = useMemo(
    () => state.uploadedFiles.find((f) => f.id === state.selectedFileId) || null,
    [state.uploadedFiles, state.selectedFileId],
  );

  const totalRows = state.uploadedFiles.reduce((a, f) => a + f.rows, 0);
  const totalSize = state.uploadedFiles.reduce((a, f) => a + f.size, 0);

  const storageCards = [
    { label: 'Total Files', value: String(state.uploadedFiles.length), icon: Upload, color: '#00C896' },
    { label: 'Total Rows', value: totalRows.toLocaleString(), icon: Database, color: '#3B82F6' },
    { label: 'Total Size', value: `${(totalSize / (1024 * 1024)).toFixed(2)} MB`, icon: Database, color: '#F6C343' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Satellite Upload</h1>
          <p className="text-sm text-text-secondary mt-0.5">Upload and manage satellite imagery datasets</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {storageCards.map((s) => (
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card padding="lg">
            <CardTitle className="mb-4">Upload Files</CardTitle>
            <DragDropZone
              onFileParsed={(file) => dispatch({ type: 'ADD_FILE', file })}
            />
          </Card>

          {selectedFile && (
            <Card padding="lg">
              <div className="flex items-center justify-between mb-4">
                <CardTitle>Data Preview</CardTitle>
                <Badge variant="info">{selectedFile.type.toUpperCase()}</Badge>
              </div>
              <DataPreview file={selectedFile} />
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card padding="lg">
            <div className="flex items-center justify-between mb-4">
              <CardTitle>Files</CardTitle>
              {state.uploadedFiles.length > 0 && (
                <span className="text-xs text-text-secondary">{state.uploadedFiles.length}</span>
              )}
            </div>
            <FileList
              files={state.uploadedFiles}
              selectedId={state.selectedFileId}
              onSelect={(id) => dispatch({ type: 'SELECT_FILE', id })}
              onDelete={(id) => dispatch({ type: 'REMOVE_FILE', id })}
              onRename={(id, name) => dispatch({ type: 'RENAME_FILE', id, name })}
              onExport={(file) => exportCSV(file.name.replace(/\.[^/.]+$/, ''), file.data)}
            />
          </Card>

          {state.uploadedFiles.length > 0 && (
            <Card padding="none" className="overflow-hidden">
              <div className="p-4 border-b border-border flex items-center gap-2">
                <MapPin className="h-4 w-4 text-accent" />
                <CardTitle>Satellite Heatmap</CardTitle>
                <Badge variant="info">{state.uploadedFiles.length} dataset{state.uploadedFiles.length !== 1 ? 's' : ''}</Badge>
              </div>
              <CanvasHeatmap className="h-[320px]" />
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
