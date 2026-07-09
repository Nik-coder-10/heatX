import { useState, useCallback, useRef } from 'react';
import { Upload, AlertCircle, CheckCircle, X } from 'lucide-react';
import { clsx } from 'clsx';
import { Button } from './Button';
import { validateFile, parseFile } from '@/utils/fileParser';
import type { UploadedFile } from '@/types';

interface DragDropZoneProps {
  onFileParsed: (file: UploadedFile) => void;
  accept?: string;
}

export function DragDropZone({ onFileParsed, accept = '.csv,.xlsx,.xls,.geojson,.json' }: DragDropZoneProps) {
  const [dragging, setDragging] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (file: File) => {
    setError(null);
    setSuccess(null);
    const validationError = validateFile(file);
    if (validationError) { setError(validationError); return; }
    setParsing(true);
    try {
      const parsed = await parseFile(file);
      onFileParsed(parsed);
      setSuccess(`Parsed ${parsed.name} (${parsed.rows} rows, ${parsed.columns.length} columns)`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to parse file');
    } finally {
      setParsing(false);
    }
  }, [onFileParsed]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const onInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    if (inputRef.current) inputRef.current.value = '';
  }, [handleFile]);

  return (
    <div>
      <div
        onDragEnter={() => setDragging(true)}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={clsx(
          'border-2 border-dashed rounded-xl p-12 text-center transition-all duration-200 cursor-pointer',
          dragging
            ? 'border-accent bg-accent/5'
            : 'border-border hover:border-accent/50 bg-surface-200/30 hover:bg-surface-200/60',
        )}
      >
        <input ref={inputRef} type="file" accept={accept} className="hidden" onChange={onInputChange} />
        <div className="w-12 h-12 rounded-xl bg-accent/10 flex items-center justify-center mx-auto mb-4">
          <Upload className="h-6 w-6 text-accent" />
        </div>
        <p className="text-sm font-medium text-text-primary mb-1">
          {parsing ? 'Parsing file...' : 'Drop files here or click to browse'}
        </p>
        <p className="text-xs text-text-secondary mb-4">Supports CSV, XLSX, GeoJSON</p>
        <Button loading={parsing} type="button" size="sm">Select Files</Button>
      </div>

      {error && (
        <div className="mt-3 flex items-center gap-2 text-xs text-danger bg-danger/10 rounded-lg p-3 border border-danger/10">
          <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" />
          <span className="flex-1">{error}</span>
          <button onClick={() => setError(null)} className="cursor-pointer"><X className="h-3.5 w-3.5" /></button>
        </div>
      )}
      {success && (
        <div className="mt-3 flex items-center gap-2 text-xs text-success bg-success/10 rounded-lg p-3 border border-success/10">
          <CheckCircle className="h-3.5 w-3.5 flex-shrink-0" />
          <span className="flex-1">{success}</span>
          <button onClick={() => setSuccess(null)} className="cursor-pointer"><X className="h-3.5 w-3.5" /></button>
        </div>
      )}
    </div>
  );
}
